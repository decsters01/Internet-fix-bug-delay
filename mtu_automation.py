#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação de Ajuste de MTU
====================================

Este módulo automatiza o ajuste do MTU (Maximum Transmission Unit) das interfaces
de rede no Windows, essencial para otimizar a conectividade e resolver problemas
de fragmentação de pacotes.

Funcionalidades:
- Detecção automática de interfaces de rede ativas
- Ajuste de MTU com validação de valores seguros
- Backup e restauração do MTU original
- Verificação de status antes/depois das operações
- Suporte a múltiplos valores padrão (1450, 1400, 1300, 1500)
- Execução segura com verificação de privilégios

Autor: Sistema de Automação
Versão: 1.0.0
Data: 2025-12-12
"""

import logging
import os
import sys
import subprocess
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Importações específicas do Windows
try:
    import ctypes
    import wmi
    import pythoncom
    from winreg import HKEY_LOCAL_MACHINE, KEY_ALL_ACCESS, REG_DWORD, REG_SZ
except ImportError as e:
    print("ERRO: Este módulo requer Python para Windows com pywin32 instalado.")
    print("Execute: pip install pywin32 wmi")
    sys.exit(1)


class MTUManager:
    """
    Gerenciador de Ajuste de MTU para Automação
    
    Esta classe fornece métodos para detectar, configurar e gerenciar
    as configurações de MTU das interfaces de rede no Windows.
    """
    
    # Valores MTU seguros e comuns
    SAFE_MTU_VALUES = {
        1500: "Padrão Ethernet (máximo para a maioria das redes)",
        1450: "Otimizado para evitar fragmentação",
        1400: "Seguro para a maioria das conexões",
        1300: "Conservative para conexões problemáticas",
        576: "Mínimo padrão para PPP"
    }
    
    # Limites seguros para MTU
    MIN_MTU = 576
    MAX_MTU = 9000
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de MTU.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando MTUManager")
        
        # Verificar se está rodando como administrador
        if not self._is_admin():
            self.logger.warning("Este módulo requer privilégios de administrador para funcionar corretamente")
        
        # Inicializar WMI
        try:
            pythoncom.CoInitialize()
            self.wmi = wmi.WMI()
            self.logger.info("WMI inicializado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar WMI: {e}")
            raise
        
        # Arquivo de backup para MTUs originais
        self.backup_file = Path("mtu_backup.json")
        
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('mtu_automation.log', encoding='utf-8')
            ]
        )
    
    def _is_admin(self) -> bool:
        """
        Verifica se o script está sendo executado com privilégios de administrador.
        
        Returns:
            bool: True se está rodando como administrador
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def _execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Executa um comando do sistema e retorna o resultado.
        
        Args:
            command (str): Comando a ser executado
            timeout (int): Tempo máximo de espera em segundos (default: 30)
            
        Returns:
            Tuple[bool, str, str]: (sucesso, stdout, stderr)
        """
        self.logger.info(f"Executando comando: {command}")
        
        try:
            # Executar o comando
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            # Logar a saída
            if result.stdout:
                self.logger.debug(f"STDOUT: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"STDERR: {result.stderr}")
            
            # Verificar sucesso
            success = result.returncode == 0
            if success:
                self.logger.info(f"Comando executado com sucesso: {command}")
            else:
                self.logger.warning(f"Comando falhou ({result.returncode}): {command}")
            
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Comando expirou após {timeout} segundos: {command}")
            return False, "", f"Timeout após {timeout} segundos"
        except Exception as e:
            self.logger.error(f"Erro ao executar comando '{command}': {e}")
            return False, "", str(e)
    
    def detect_network_interfaces(self) -> List[Dict]:
        """
        Detecta todas as interfaces de rede disponíveis no sistema.
        
        Returns:
            List[Dict]: Lista de interfaces com informações detalhadas
        """
        self.logger.info("Iniciando detecção de interfaces de rede")
        interfaces = []
        
        try:
            # Obter interfaces via netsh
            success, stdout, stderr = self._execute_command('netsh interface ipv4 show subinterfaces', 15)
            
            if success:
                lines = stdout.split('\n')
                for line in lines:
                    # Parse das linhas que contêm informações de interface
                    if 'connected' in line.lower() or 'disconnected' in line.lower():
                        parts = line.split()
                        if len(parts) >= 4:
                            interface_name = ' '.join(parts[:-2])  # Nome pode ter espaços
                            try:
                                mtu = int(parts[-2])
                                status = parts[-1]
                                
                                interface_info = {
                                    'name': interface_name.strip(),
                                    'mtu': mtu,
                                    'status': status,
                                    'type': 'netsh'
                                }
                                interfaces.append(interface_info)
                                self.logger.info(f"Interface detectada: {interface_name} (MTU: {mtu}, Status: {status})")
                            except (ValueError, IndexError):
                                continue
            
            # Complementar com informações do WMI
            for nic in self.wmi.Win32_NetworkAdapter(NetConnectionStatus=2):
                if nic.NetConnectionID:
                    # Verificar se já existe na lista
                    existing = next((i for i in interfaces if i['name'] == nic.NetConnectionID), None)
                    if not existing:
                        interface_info = {
                            'name': nic.NetConnectionID,
                            'mtu': 1500,  # Valor padrão se não conseguir detectar
                            'status': 'connected',
                            'type': 'wmi',
                            'device_id': nic.DeviceID,
                            'description': nic.Description
                        }
                        interfaces.append(interface_info)
                        self.logger.info(f"Interface WMI detectada: {nic.NetConnectionID}")
            
            self.logger.info(f"Total de interfaces detectadas: {len(interfaces)}")
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar interfaces de rede: {e}")
            raise
    
    def get_current_mtu(self, interface_name: str) -> Optional[int]:
        """
        Obtém o MTU atual de uma interface específica.
        
        Args:
            interface_name (str): Nome da interface
            
        Returns:
            Optional[int]: MTU atual ou None se não conseguir obter
        """
        self.logger.info(f"Obtendo MTU atual para interface: {interface_name}")
        
        try:
            success, stdout, stderr = self._execute_command(
                f'netsh interface ipv4 show subinterface "{interface_name}"', 10
            )
            
            if success:
                lines = stdout.split('\n')
                for line in lines:
                    if interface_name in line and 'connected' in line.lower():
                        parts = line.split()
                        try:
                            mtu = int(parts[-2])
                            self.logger.info(f"MTU atual da interface {interface_name}: {mtu}")
                            return mtu
                        except (ValueError, IndexError):
                            continue
            
            self.logger.warning(f"Não foi possível obter MTU da interface {interface_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao obter MTU da interface {interface_name}: {e}")
            return None
    
    def validate_mtu_value(self, mtu_value: int) -> Tuple[bool, str]:
        """
        Valida se um valor MTU está dentro de limites seguros.
        
        Args:
            mtu_value (int): Valor MTU a ser validado
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem)
        """
        if not isinstance(mtu_value, int):
            return False, "Valor MTU deve ser um número inteiro"
        
        if mtu_value < self.MIN_MTU:
            return False, f"MTU muito baixo. Mínimo permitido: {self.MIN_MTU}"
        
        if mtu_value > self.MAX_MTU:
            return False, f"MTU muito alto. Máximo permitido: {self.MAX_MTU}"
        
        if mtu_value in self.SAFE_MTU_VALUES:
            return True, f"MTU válido: {self.SAFE_MTU_VALUES[mtu_value]}"
        else:
            return True, f"MTU válido (fora dos valores padrão recomendados)"
    
    def backup_current_mtus(self) -> bool:
        """
        Faz backup dos MTUs atuais de todas as interfaces.
        
        Returns:
            bool: True se o backup foi bem-sucedido
        """
        self.logger.info("Iniciando backup dos MTUs atuais")
        
        try:
            interfaces = self.detect_network_interfaces()
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'interfaces': {}
            }
            
            for interface in interfaces:
                current_mtu = self.get_current_mtu(interface['name'])
                if current_mtu is not None:
                    backup_data['interfaces'][interface['name']] = {
                        'original_mtu': current_mtu,
                        'status': interface['status'],
                        'description': interface.get('description', '')
                    }
            
            # Salvar backup
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Backup salvo em: {self.backup_file}")
            self.logger.info(f"Backup concluído para {len(backup_data['interfaces'])} interfaces")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao fazer backup dos MTUs: {e}")
            return False
    
    def restore_original_mtus(self) -> bool:
        """
        Restaura os MTUs originais a partir do backup.
        
        Returns:
            bool: True se a restauração foi bem-sucedida
        """
        self.logger.info("Iniciando restauração dos MTUs originais")
        
        try:
            if not self.backup_file.exists():
                self.logger.error("Arquivo de backup não encontrado")
                return False
            
            # Carregar backup
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            success_count = 0
            total_count = len(backup_data['interfaces'])
            
            for interface_name, interface_data in backup_data['interfaces'].items():
                original_mtu = interface_data['original_mtu']
                
                try:
                    if self._set_mtu(interface_name, original_mtu):
                        success_count += 1
                        self.logger.info(f"MTU restaurado para {interface_name}: {original_mtu}")
                    else:
                        self.logger.error(f"Falha ao restaurar MTU para {interface_name}")
                except Exception as e:
                    self.logger.error(f"Erro ao restaurar MTU para {interface_name}: {e}")
            
            self.logger.info(f"Restauração concluída: {success_count}/{total_count} interfaces")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar MTUs originais: {e}")
            return False
    
    def _set_mtu(self, interface_name: str, mtu_value: int) -> bool:
        """
        Define o MTU para uma interface específica.
        
        Args:
            interface_name (str): Nome da interface
            mtu_value (int): Novo valor MTU
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info(f"Definindo MTU {mtu_value} para interface {interface_name}")
        
        try:
            command = f'netsh interface ipv4 set subinterface "{interface_name}" mtu={mtu_value} store=persistent'
            success, stdout, stderr = self._execute_command(command, 15)
            
            if success:
                self.logger.info(f"MTU definido com sucesso para {interface_name}: {mtu_value}")
                return True
            else:
                self.logger.error(f"Falha ao definir MTU para {interface_name}: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao definir MTU para {interface_name}: {e}")
            return False
    
    def set_mtu(self, interface_name: str, mtu_value: int, backup_first: bool = True) -> bool:
        """
        Define o MTU para uma interface específica com validação e backup opcional.
        
        Args:
            interface_name (str): Nome da interface
            mtu_value (int): Novo valor MTU
            backup_first (bool): Se deve fazer backup antes da alteração
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info(f"Iniciando ajuste de MTU para interface {interface_name}")
        
        try:
            # Validar valor MTU
            is_valid, message = self.validate_mtu_value(mtu_value)
            if not is_valid:
                self.logger.error(f"Valor MTU inválido: {message}")
                return False
            
            self.logger.info(f"Validação MTU: {message}")
            
            # Fazer backup se solicitado
            if backup_first:
                if not self.backup_current_mtus():
                    self.logger.warning("Falha no backup, continuando sem backup")
            
            # Obter MTU atual
            current_mtu = self.get_current_mtu(interface_name)
            if current_mtu == mtu_value:
                self.logger.info(f"Interface {interface_name} já tem MTU {mtu_value}")
                return True
            
            # Definir novo MTU
            if self._set_mtu(interface_name, mtu_value):
                self.logger.info(f"MTU ajustado com sucesso: {interface_name} ({current_mtu} -> {mtu_value})")
                return True
            else:
                self.logger.error(f"Falha ao ajustar MTU para {interface_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao ajustar MTU para {interface_name}: {e}")
            return False
    
    def set_mtu_for_all_interfaces(self, mtu_value: int, backup_first: bool = True) -> bool:
        """
        Define o MTU para todas as interfaces ativas.
        
        Args:
            mtu_value (int): Novo valor MTU
            backup_first (bool): Se deve fazer backup antes da alteração
            
        Returns:
            bool: True se a operação foi bem-sucedida para pelo menos uma interface
        """
        self.logger.info(f"Iniciando ajuste de MTU para todas as interfaces (valor: {mtu_value})")
        
        try:
            # Validar valor MTU
            is_valid, message = self.validate_mtu_value(mtu_value)
            if not is_valid:
                self.logger.error(f"Valor MTU inválido: {message}")
                return False
            
            self.logger.info(f"Validação MTU: {message}")
            
            # Fazer backup se solicitado
            if backup_first:
                if not self.backup_current_mtus():
                    self.logger.warning("Falha no backup, continuando sem backup")
            
            # Obter interfaces
            interfaces = self.detect_network_interfaces()
            connected_interfaces = [i for i in interfaces if i['status'] == 'connected']
            
            if not connected_interfaces:
                self.logger.warning("Nenhuma interface conectada encontrada")
                return False
            
            success_count = 0
            total_count = len(connected_interfaces)
            
            for interface in connected_interfaces:
                interface_name = interface['name']
                current_mtu = interface['mtu']
                
                if current_mtu == mtu_value:
                    self.logger.info(f"Interface {interface_name} já tem MTU {mtu_value}")
                    continue
                
                try:
                    if self._set_mtu(interface_name, mtu_value):
                        success_count += 1
                        self.logger.info(f"MTU ajustado: {interface_name} ({current_mtu} -> {mtu_value})")
                    else:
                        self.logger.error(f"Falha ao ajustar MTU para {interface_name}")
                except Exception as e:
                    self.logger.error(f"Erro ao ajustar MTU para {interface_name}: {e}")
            
            self.logger.info(f"Ajuste de MTU concluído: {success_count}/{total_count} interfaces")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao ajustar MTU para todas as interfaces: {e}")
            return False
    
    def get_mtu_status(self, interface_name: Optional[str] = None) -> Dict:
        """
        Obtém o status atual do MTU das interfaces.
        
        Args:
            interface_name (str, optional): Nome específico da interface para verificar
            
        Returns:
            Dict: Status detalhado das interfaces
        """
        self.logger.info(f"Verificando status de MTU para: {interface_name or 'todas as interfaces'}")
        
        try:
            interfaces = self.detect_network_interfaces()
            status_info = {
                'timestamp': datetime.now().isoformat(),
                'interfaces': {},
                'summary': {
                    'total_interfaces': 0,
                    'connected_interfaces': 0,
                    'mtu_values': {},
                    'recommended_values': self.SAFE_MTU_VALUES
                }
            }
            
            for interface in interfaces:
                if interface_name and interface['name'] != interface_name:
                    continue
                
                interface_status = {
                    'name': interface['name'],
                    'current_mtu': interface['mtu'],
                    'status': interface['status'],
                    'is_recommended': interface['mtu'] in self.SAFE_MTU_VALUES,
                    'validation_message': None
                }
                
                # Validar MTU atual
                is_valid, message = self.validate_mtu_value(interface['mtu'])
                interface_status['is_valid'] = is_valid
                interface_status['validation_message'] = message
                
                status_info['interfaces'][interface['name']] = interface_status
                
                # Atualizar resumo
                status_info['summary']['total_interfaces'] += 1
                if interface['status'] == 'connected':
                    status_info['summary']['connected_interfaces'] += 1
                
                # Contar valores MTU
                mtu_str = str(interface['mtu'])
                status_info['summary']['mtu_values'][mtu_str] = \
                    status_info['summary']['mtu_values'].get(mtu_str, 0) + 1
            
            self.logger.info("Verificação de status de MTU concluída")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status de MTU: {e}")
            raise
    
    def list_recommended_mtu_values(self) -> Dict[int, str]:
        """
        Lista os valores MTU recomendados.
        
        Returns:
            Dict[int, str]: Dicionário com valores MTU e suas descrições
        """
        return self.SAFE_MTU_VALUES.copy()
    
    def __del__(self):
        """Limpeza ao destruir o objeto."""
        try:
            pythoncom.CoUninitialize()
        except:
            pass


# Funções de conveniência para uso direto
def set_mtu_interface(interface_name: str, mtu_value: int, backup_first: bool = True):
    """
    Define o MTU para uma interface específica.
    
    Args:
        interface_name (str): Nome da interface
        mtu_value (int): Novo valor MTU
        backup_first (bool): Se deve fazer backup antes da alteração
    """
    manager = MTUManager()
    return manager.set_mtu(interface_name, mtu_value, backup_first)


def set_mtu_all_interfaces(mtu_value: int, backup_first: bool = True):
    """
    Define o MTU para todas as interfaces ativas.
    
    Args:
        mtu_value (int): Novo valor MTU
        backup_first (bool): Se deve fazer backup antes da alteração
    """
    manager = MTUManager()
    return manager.set_mtu_for_all_interfaces(mtu_value, backup_first)


def get_mtu_status(interface_name: Optional[str] = None):
    """
    Obtém o status atual do MTU das interfaces.
    
    Args:
        interface_name (str, optional): Nome específico da interface para verificar
    """
    manager = MTUManager()
    return manager.get_mtu_status(interface_name)


def list_network_interfaces():
    """Lista todas as interfaces de rede disponíveis."""
    manager = MTUManager()
    return manager.detect_network_interfaces()


def backup_mtus():
    """Faz backup dos MTUs atuais de todas as interfaces."""
    manager = MTUManager()
    return manager.backup_current_mtus()


def restore_original_mtus():
    """Restaura os MTUs originais a partir do backup."""
    manager = MTUManager()
    return manager.restore_original_mtus()


def get_recommended_mtu_values():
    """Lista os valores MTU recomendados."""
    manager = MTUManager()
    return manager.list_recommended_mtu_values()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação de Ajuste de MTU ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = MTUManager()
        
        # Verificar se está rodando como administrador
        if not manager._is_admin():
            print("⚠️  AVISO: Este script requer privilégios de administrador para funcionar corretamente")
            print("   Execute o prompt de comando como administrador e tente novamente")
            print()
        
        # Listar interfaces disponíveis
        print("1. Interfaces de Rede Disponíveis:")
        interfaces = manager.detect_network_interfaces()
        for i, interface in enumerate(interfaces, 1):
            print(f"   {i}. {interface['name']} (MTU: {interface['mtu']}, Status: {interface['status']})")
        print()
        
        # Mostrar valores recomendados
        print("2. Valores MTU Recomendados:")
        for mtu_value, description in manager.list_recommended_mtu_values().items():
            print(f"   {mtu_value}: {description}")
        print()
        
        # Verificar status atual
        print("3. Status Atual do MTU:")
        status = manager.get_mtu_status()
        for interface_name, interface_status in status['interfaces'].items():
            validation_icon = "✓" if interface_status['is_valid'] else "✗"
            recommended_icon = "★" if interface_status['is_recommended'] else " "
            print(f"   {validation_icon}{recommended_icon} {interface_name}: {interface_status['current_mtu']} - {interface_status['validation_message']}")
        print()
        
        # Exemplo de ajuste (comentado para segurança)
        print("4. Exemplo de Ajuste de MTU:")
        print("   Para ajustar o MTU para 1450 em todas as interfaces, descomente abaixo:")
        print("   # success = manager.set_mtu_for_all_interfaces(1450)")
        print("   # if success:")
        print("   #     print('   ✓ MTU ajustado com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha ao ajustar MTU')")
        print()
        
        # Exemplo de backup/restauração
        print("5. Backup e Restauração:")
        print("   Para fazer backup dos MTUs atuais:")
        print("   # manager.backup_current_mtus()")
        print("   Para restaurar MTUs originais:")
        print("   # manager.restore_original_mtus()")
        print()
        
        print("Operação concluída!")
        print()
        print("💡 DICA: Após ajustar o MTU, teste a conectividade para verificar se melhorou")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")
