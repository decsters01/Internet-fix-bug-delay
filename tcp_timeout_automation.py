#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação de Timeout TCP
==================================

Este módulo automatiza o aumento do timeout TCP no registro do Windows,
essencial para otimizar conexões e evitar erros de "Time limit expired"
em aplicações como WebSocket e trading.

Funcionalidades:
- Configurar TcpMaxDataRetransmissions (valor: 10)
- Configurar KeepAliveTime (valor: 7200000)
- Backup e restauração das configurações originais
- Verificação de status das configurações TCP
- Validação de valores seguros
- Execução segura com verificação de privilégios

Autor: Sistema de Automação
Versão: 1.0.0
Data: 2025-12-12
"""

import logging
import os
import sys
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Importações específicas do Windows
try:
    import ctypes
    import winreg
    from winreg import HKEY_LOCAL_MACHINE, KEY_ALL_ACCESS, KEY_READ, REG_DWORD, REG_SZ
except ImportError as e:
    print("ERRO: Este módulo requer Python para Windows com pywin32 instalado.")
    print("Execute: pip install pywin32")
    sys.exit(1)


class TCPTimeoutManager:
    """
    Gerenciador de Timeout TCP para Automação
    
    Esta classe fornece métodos para configurar, verificar e gerenciar
    as configurações de timeout TCP no registro do Windows.
    """
    
    # Caminho do registro TCP/IP
    TCP_REGISTRY_PATH = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
    
    # Configurações TCP timeout
    TCP_TIMEOUT_SETTINGS = {
        'TcpMaxDataRetransmissions': {
            'value': 10,
            'description': 'Número máximo de retransmissões de dados TCP',
            'default_value': 3,
            'type': REG_DWORD
        },
        'KeepAliveTime': {
            'value': 7200000,
            'description': 'Tempo em milissegundos antes do primeiro keep-alive',
            'default_value': 7200000,
            'type': REG_DWORD
        }
    }
    
    # Limites seguros para validação
    MIN_KEEPALIVE_TIME = 60000  # 1 minuto
    MAX_KEEPALIVE_TIME = 4294967295  # UINT32_MAX
    MIN_MAX_RETRANSMISSIONS = 1
    MAX_MAX_RETRANSMISSISSIONS = 255
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de timeout TCP.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando TCPTimeoutManager")
        
        # Verificar se está rodando como administrador
        if not self._is_admin():
            self.logger.warning("Este módulo requer privilégios de administrador para funcionar corretamente")
        
        # Arquivo de backup para configurações originais
        self.backup_file = Path("tcp_timeout_backup.json")
        
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('tcp_timeout_automation.log', encoding='utf-8')
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
    
    def _backup_current_settings(self) -> Dict:
        """
        Faz backup das configurações TCP atuais.
        
        Returns:
            Dict: Configurações TCP atuais
        """
        backup = {
            'timestamp': datetime.now().isoformat(),
            'settings': {}
        }
        
        self.logger.info("Fazendo backup das configurações TCP atuais")
        
        try:
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, self.TCP_REGISTRY_PATH, 0, KEY_READ) as key:
                for setting_name, setting_info in self.TCP_TIMEOUT_SETTINGS.items():
                    try:
                        current_value, _ = winreg.QueryValueEx(key, setting_name)
                        backup['settings'][setting_name] = {
                            'current_value': current_value,
                            'description': setting_info['description']
                        }
                        self.logger.info(f"Backup {setting_name}: {current_value}")
                    except FileNotFoundError:
                        backup['settings'][setting_name] = {
                            'current_value': None,
                            'description': setting_info['description']
                        }
                        self.logger.info(f"Configuração {setting_name} não encontrada (será criada)")
                        
        except Exception as e:
            self.logger.error(f"Erro ao fazer backup das configurações: {e}")
            raise
        
        return backup
    
    def _save_backup(self, backup_data: Dict) -> bool:
        """
        Salva o backup das configurações TCP em arquivo JSON.
        
        Args:
            backup_data (Dict): Dados do backup
            
        Returns:
            bool: True se salvo com sucesso
        """
        try:
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Backup salvo em: {self.backup_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar backup: {e}")
            return False
    
    def _load_backup(self) -> Optional[Dict]:
        """
        Carrega o backup das configurações TCP do arquivo JSON.
        
        Returns:
            Optional[Dict]: Dados do backup ou None se não encontrado
        """
        try:
            if self.backup_file.exists():
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                self.logger.info(f"Backup carregado de: {self.backup_file}")
                return backup_data
        except Exception as e:
            self.logger.error(f"Erro ao carregar backup: {e}")
        return None
    
    def validate_tcp_setting(self, setting_name: str, value: int) -> Tuple[bool, str]:
        """
        Valida se um valor de configuração TCP está dentro de limites seguros.
        
        Args:
            setting_name (str): Nome da configuração
            value (int): Valor a ser validado
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem)
        """
        if setting_name not in self.TCP_TIMEOUT_SETTINGS:
            return False, f"Configuração '{setting_name}' não reconhecida"
        
        if not isinstance(value, int):
            return False, f"Valor deve ser um número inteiro"
        
        if setting_name == 'KeepAliveTime':
            if value < self.MIN_KEEPALIVE_TIME:
                return False, f"KeepAliveTime muito baixo. Mínimo: {self.MIN_KEEPALIVE_TIME}ms"
            if value > self.MAX_KEEPALIVE_TIME:
                return False, f"KeepAliveTime muito alto. Máximo: {self.MAX_KEEPALIVE_TIME}"
        
        elif setting_name == 'TcpMaxDataRetransmissions':
            if value < self.MIN_MAX_RETRANSMISSIONS:
                return False, f"TcpMaxDataRetransmissions muito baixo. Mínimo: {self.MIN_MAX_RETRANSMISSIONS}"
            if value > self.MAX_MAX_RETRANSMISSISSIONS:
                return False, f"TcpMaxDataRetransmissions muito alto. Máximo: {self.MAX_MAX_RETRANSMISSISSIONS}"
        
        return True, f"Valor válido para {setting_name}"
    
    def configure_tcp_timeout(self, backup_first: bool = True) -> bool:
        """
        Configura as configurações de timeout TCP otimizadas.
        
        Args:
            backup_first (bool): Se deve fazer backup antes da alteração
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando configuração de timeout TCP otimizado")
        
        try:
            # Fazer backup se solicitado
            if backup_first:
                backup_data = self._backup_current_settings()
                if not self._save_backup(backup_data):
                    self.logger.warning("Falha no backup, continuando sem backup")
            
            success_count = 0
            total_count = len(self.TCP_TIMEOUT_SETTINGS)
            
            # Abrir chave do registro com permissão de escrita
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, self.TCP_REGISTRY_PATH, 0, KEY_ALL_ACCESS) as key:
                for setting_name, setting_info in self.TCP_TIMEOUT_SETTINGS.items():
                    try:
                        # Validar valor
                        is_valid, message = self.validate_tcp_setting(setting_name, setting_info['value'])
                        if not is_valid:
                            self.logger.error(f"Valor inválido para {setting_name}: {message}")
                            continue
                        
                        # Criar ou atualizar valor
                        winreg.SetValueEx(
                            key, 
                            setting_name, 
                            0, 
                            setting_info['type'], 
                            setting_info['value']
                        )
                        
                        self.logger.info(f"Configuração aplicada: {setting_name} = {setting_info['value']}")
                        self.logger.info(f"Descrição: {setting_info['description']}")
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao configurar {setting_name}: {e}")
            
            self.logger.info(f"Configuração concluída: {success_count}/{total_count} configurações aplicadas")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar timeout TCP: {e}")
            raise
    
    def restore_original_settings(self) -> bool:
        """
        Restaura as configurações TCP originais a partir do backup.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando restauração das configurações TCP originais")
        
        backup_data = self._load_backup()
        if not backup_data:
            self.logger.error("Nenhum backup encontrado para restaurar")
            return False
        
        try:
            success_count = 0
            total_count = len(backup_data['settings'])
            
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, self.TCP_REGISTRY_PATH, 0, KEY_ALL_ACCESS) as key:
                for setting_name, setting_data in backup_data['settings'].items():
                    try:
                        current_value = setting_data['current_value']
                        
                        if current_value is None:
                            # Configuração não existia, tentar remover
                            try:
                                winreg.DeleteValue(key, setting_name)
                                self.logger.info(f"Configuração {setting_name} removida (não existia originalmente)")
                                success_count += 1
                            except FileNotFoundError:
                                self.logger.info(f"Configuração {setting_name} já não existe")
                                success_count += 1
                        else:
                            # Restaurar valor original
                            winreg.SetValueEx(
                                key,
                                setting_name,
                                0,
                                REG_DWORD,
                                current_value
                            )
                            self.logger.info(f"Configuração {setting_name} restaurada: {current_value}")
                            success_count += 1
                            
                    except Exception as e:
                        self.logger.error(f"Erro ao restaurar {setting_name}: {e}")
            
            self.logger.info(f"Restauração concluída: {success_count}/{total_count} configurações restauradas")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar configurações: {e}")
            raise
    
    def check_tcp_status(self) -> Dict:
        """
        Verifica o status atual das configurações TCP.
        
        Returns:
            Dict: Status detalhado das configurações TCP
        """
        self.logger.info("Verificando status das configurações TCP")
        
        status_info = {
            'timestamp': datetime.now().isoformat(),
            'settings': {},
            'summary': {
                'total_settings': len(self.TCP_TIMEOUT_SETTINGS),
                'configured_correctly': 0,
                'needs_update': 0,
                'not_found': 0
            }
        }
        
        try:
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, self.TCP_REGISTRY_PATH, 0, KEY_READ) as key:
                for setting_name, setting_info in self.TCP_TIMEOUT_SETTINGS.items():
                    setting_status = {
                        'name': setting_name,
                        'description': setting_info['description'],
                        'current_value': None,
                        'expected_value': setting_info['value'],
                        'is_configured': False,
                        'needs_update': False
                    }
                    
                    try:
                        current_value, _ = winreg.QueryValueEx(key, setting_name)
                        setting_status['current_value'] = current_value
                        
                        if current_value == setting_info['value']:
                            setting_status['is_configured'] = True
                            status_info['summary']['configured_correctly'] += 1
                            self.logger.info(f"{setting_name}: ✓ Configurado corretamente ({current_value})")
                        else:
                            setting_status['needs_update'] = True
                            status_info['summary']['needs_update'] += 1
                            self.logger.warning(f"{setting_name}: ⚠ Valor incorreto (atual: {current_value}, esperado: {setting_info['value']})")
                            
                    except FileNotFoundError:
                        setting_status['needs_update'] = True
                        status_info['summary']['not_found'] += 1
                        self.logger.warning(f"{setting_name}: ⚠ Configuração não encontrada")
                    
                    status_info['settings'][setting_name] = setting_status
            
            self.logger.info("Verificação de status TCP concluída")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status TCP: {e}")
            raise
    
    def get_recommended_settings(self) -> Dict:
        """
        Obtém as configurações TCP recomendadas.
        
        Returns:
            Dict: Configurações recomendadas com descrições
        """
        return {
            name: {
                'value': info['value'],
                'description': info['description'],
                'type': 'DWORD (32-bit)'
            }
            for name, info in self.TCP_TIMEOUT_SETTINGS.items()
        }
    
    def test_tcp_connection(self, host: str = "8.8.8.8", port: int = 53, timeout: int = 10) -> Tuple[bool, str]:
        """
        Testa uma conexão TCP para verificar se as configurações estão funcionando.
        
        Args:
            host (str): Host para testar (default: 8.8.8.8)
            port (int): Porta para testar (default: 53)
            timeout (int): Timeout da conexão em segundos (default: 10)
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        self.logger.info(f"Testando conexão TCP para {host}:{port}")
        
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                message = f"Conexão TCP bem-sucedida para {host}:{port}"
                self.logger.info(message)
                return True, message
            else:
                message = f"Falha na conexão TCP para {host}:{port} (código: {result})"
                self.logger.warning(message)
                return False, message
                
        except Exception as e:
            message = f"Erro ao testar conexão TCP: {e}"
            self.logger.error(message)
            return False, message
    
    def __del__(self):
        """Limpeza ao destruir o objeto."""
        pass


# Funções de conveniência para uso direto
def configure_tcp_timeout(backup_first: bool = True):
    """
    Configura as configurações de timeout TCP otimizadas.
    
    Args:
        backup_first (bool): Se deve fazer backup antes da alteração
    """
    manager = TCPTimeoutManager()
    return manager.configure_tcp_timeout(backup_first)


def restore_tcp_settings():
    """Restaura as configurações TCP originais do backup."""
    manager = TCPTimeoutManager()
    return manager.restore_original_settings()


def check_tcp_status():
    """Verifica o status atual das configurações TCP."""
    manager = TCPTimeoutManager()
    return manager.check_tcp_status()


def get_tcp_recommended_settings():
    """Obtém as configurações TCP recomendadas."""
    manager = TCPTimeoutManager()
    return manager.get_recommended_settings()


def test_tcp_connection(host: str = "8.8.8.8", port: int = 53, timeout: int = 10):
    """
    Testa uma conexão TCP.
    
    Args:
        host (str): Host para testar
        port (int): Porta para testar
        timeout (int): Timeout da conexão em segundos
    """
    manager = TCPTimeoutManager()
    return manager.test_tcp_connection(host, port, timeout)


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação de Timeout TCP ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = TCPTimeoutManager()
        
        # Verificar se está rodando como administrador
        if not manager._is_admin():
            print("⚠️  AVISO: Este script requer privilégios de administrador para funcionar corretamente")
            print("   Execute o prompt de comando como administrador e tente novamente")
            print()
        
        # Mostrar configurações recomendadas
        print("1. Configurações TCP Recomendadas:")
        recommended = manager.get_recommended_settings()
        for setting_name, setting_info in recommended.items():
            print(f"   {setting_name}:")
            print(f"     Valor: {setting_info['value']}")
            print(f"     Descrição: {setting_info['description']}")
            print(f"     Tipo: {setting_info['type']}")
            print()
        
        # Verificar status atual
        print("2. Status Atual das Configurações TCP:")
        status = manager.check_tcp_status()
        for setting_name, setting_info in status['settings'].items():
            if setting_info['is_configured']:
                print(f"   ✓ {setting_name}: {setting_info['current_value']} (correto)")
            elif setting_info['needs_update']:
                if setting_info['current_value'] is not None:
                    print(f"   ⚠ {setting_name}: {setting_info['current_value']} (deveria ser {setting_info['expected_value']})")
                else:
                    print(f"   ✗ {setting_name}: Não encontrado (deveria ser {setting_info['expected_value']})")
        print()
        
        # Testar conexão atual
        print("3. Teste de Conectividade:")
        success, message = manager.test_tcp_connection()
        if success:
            print(f"   ✓ {message}")
        else:
            print(f"   ✗ {message}")
        print()
        
        # Exemplo de configuração (comentado para segurança)
        print("4. Exemplo de Configuração:")
        print("   Para configurar timeout TCP otimizado, descomente abaixo:")
        print("   # success = manager.configure_tcp_timeout()")
        print("   # if success:")
        print("   #     print('   ✓ Timeout TCP configurado com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha ao configurar timeout TCP')")
        print()
        
        # Exemplo de backup/restauração
        print("5. Backup e Restauração:")
        print("   Para fazer backup das configurações atuais:")
        print("   # backup_data = manager._backup_current_settings()")
        print("   # manager._save_backup(backup_data)")
        print("   Para restaurar configurações originais:")
        print("   # manager.restore_original_settings()")
        print()
        
        print("Operação concluída!")
        print()
        print("💡 DICA: Após configurar o timeout TCP, teste a conectividade para verificar se melhorou")
        print("💡 DICA: As configurações só terão efeito após reiniciar o sistema")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")
