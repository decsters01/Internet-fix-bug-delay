#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação de Reset de Rede
====================================

Este módulo automatiza a execução de comandos de reset de rede no Windows,
essencial para resolver problemas de conectividade e corrupção da pilha de rede.

Funcionalidades:
- Reset completo do Winsock (netsh winsock reset)
- Reset das configurações IP (netsh int ip reset)
- Liberação de configurações IP (ipconfig /release)
- Renovação de configurações IP (ipconfig /renew)
- Limpeza do cache DNS (ipconfig /flushdns)
- Execução sequencial de todos os comandos
- Verificação de status antes/depois das operações

Autor: Sistema de Automação
Versão: 1.0.0
Data: 2025-12-12
"""

import logging
import os
import sys
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Importações específicas do Windows
try:
    import ctypes
    import winreg
    import wmi
    import pythoncom
    from winreg import HKEY_LOCAL_MACHINE, KEY_ALL_ACCESS, REG_DWORD
except ImportError as e:
    print("ERRO: Este módulo requer Python para Windows com pywin32 instalado.")
    print("Execute: pip install pywin32 wmi")
    sys.exit(1)


class NetworkResetManager:
    """
    Gerenciador de Reset de Rede para Automação
    
    Esta classe fornece métodos para executar comandos de reset de rede
    no Windows, essencial para resolver problemas de conectividade.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de reset de rede.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando NetworkResetManager")
        
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
        
        # Comandos de reset
        self.RESET_COMMANDS = {
            'winsock': 'netsh winsock reset',
            'ip': 'netsh int ip reset',
            'release': 'ipconfig /release',
            'renew': 'ipconfig /renew',
            'flushdns': 'ipconfig /flushdns'
        }
    
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('network_reset_automation.log', encoding='utf-8')
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
    
    def _get_network_status(self) -> Dict:
        """
        Obtém o status atual da rede antes/depois das operações.
        
        Returns:
            Dict: Status detalhado da rede
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'adapters': [],
            'dns_cache_size': 0,
            'routes_count': 0
        }
        
        try:
            # Obter adaptadores de rede
            for adapter in self.wmi.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                adapter_info = {
                    'description': adapter.Description,
                    'ip_address': adapter.IPAddress[0] if adapter.IPAddress else None,
                    'subnet_mask': adapter.IPSubnet[0] if adapter.IPSubnet else None,
                    'default_gateway': adapter.DefaultIPGateway[0] if adapter.DefaultIPGateway else None,
                    'dhcp_enabled': adapter.DHCPEnabled,
                    'dns_servers': adapter.DNSServerSearchOrder if adapter.DNSServerSearchOrder else []
                }
                status['adapters'].append(adapter_info)
            
            # Obter tamanho do cache DNS (aproximado)
            try:
                success, stdout, stderr = self._execute_command('ipconfig /displaydns', 10)
                if success:
                    status['dns_cache_size'] = stdout.count('Record Name')
            except:
                pass
            
            # Obter número de rotas
            try:
                success, stdout, stderr = self._execute_command('route print', 10)
                if success:
                    status['routes_count'] = len([line for line in stdout.split('\n') if '0.0.0.0' in line])
            except:
                pass
                
        except Exception as e:
            self.logger.warning(f"Não foi possível obter status da rede: {e}")
        
        return status
    
    def reset_winsock(self) -> bool:
        """
        Executa o reset completo do Winsock.
        Corrige corrupções no socket que geram o erro 121.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando reset do Winsock")
        
        try:
            # Obter status antes
            status_before = self._get_network_status()
            self.logger.info(f"Status antes do reset: {len(status_before['adapters'])} adaptadores ativos")
            
            # Executar comando
            success, stdout, stderr = self._execute_command(self.RESET_COMMANDS['winsock'])
            
            if success:
                self.logger.info("Reset do Winsock concluído com sucesso")
            else:
                self.logger.error(f"Falha no reset do Winsock: {stderr}")
            
            # Obter status depois
            status_after = self._get_network_status()
            self.logger.info(f"Status após o reset: {len(status_after['adapters'])} adaptadores ativos")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar reset do Winsock: {e}")
            return False
    
    def reset_ip_configuration(self) -> bool:
        """
        Executa o reset das configurações IP.
        Restaura as configurações de protocolo TCP/IP para o padrão.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando reset das configurações IP")
        
        try:
            # Obter status antes
            status_before = self._get_network_status()
            self.logger.info(f"Status antes do reset: {len(status_before['adapters'])} adaptadores ativos")
            
            # Executar comando
            success, stdout, stderr = self._execute_command(self.RESET_COMMANDS['ip'])
            
            if success:
                self.logger.info("Reset das configurações IP concluído com sucesso")
            else:
                self.logger.error(f"Falha no reset das configurações IP: {stderr}")
            
            # Obter status depois
            status_after = self._get_network_status()
            self.logger.info(f"Status após o reset: {len(status_after['adapters'])} adaptadores ativos")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar reset das configurações IP: {e}")
            return False
    
    def release_ip_configuration(self) -> bool:
        """
        Libera as configurações IP atuais.
        Útil antes de renovar as configurações.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Liberando configurações IP")
        
        try:
            # Obter status antes
            status_before = self._get_network_status()
            self.logger.info(f"Status antes da liberação: {len(status_before['adapters'])} adaptadores ativos")
            
            # Executar comando
            success, stdout, stderr = self._execute_command(self.RESET_COMMANDS['release'])
            
            if success:
                self.logger.info("Liberação de configurações IP concluída com sucesso")
            else:
                self.logger.error(f"Falha na liberação de configurações IP: {stderr}")
            
            # Obter status depois
            status_after = self._get_network_status()
            self.logger.info(f"Status após a liberação: {len(status_after['adapters'])} adaptadores ativos")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao liberar configurações IP: {e}")
            return False
    
    def renew_ip_configuration(self) -> bool:
        """
        Renova as configurações IP.
        Obtém novos endereços IP do servidor DHCP.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Renovando configurações IP")
        
        try:
            # Obter status antes
            status_before = self._get_network_status()
            self.logger.info(f"Status antes da renovação: {len(status_before['adapters'])} adaptadores ativos")
            
            # Executar comando
            success, stdout, stderr = self._execute_command(self.RESET_COMMANDS['renew'])
            
            if success:
                self.logger.info("Renovação de configurações IP concluída com sucesso")
            else:
                self.logger.error(f"Falha na renovação de configurações IP: {stderr}")
            
            # Obter status depois
            status_after = self._get_network_status()
            self.logger.info(f"Status após a renovação: {len(status_after['adapters'])} adaptadores ativos")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao renovar configurações IP: {e}")
            return False
    
    def flush_dns_cache(self) -> bool:
        """
        Limpa o cache DNS.
        Remove entradas DNS corrompidas ou desatualizadas.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Limpando cache DNS")
        
        try:
            # Obter status antes
            status_before = self._get_network_status()
            self.logger.info(f"Tamanho do cache DNS antes da limpeza: {status_before['dns_cache_size']} entradas")
            
            # Executar comando
            success, stdout, stderr = self._execute_command(self.RESET_COMMANDS['flushdns'])
            
            if success:
                self.logger.info("Limpeza do cache DNS concluída com sucesso")
            else:
                self.logger.error(f"Falha na limpeza do cache DNS: {stderr}")
            
            # Obter status depois
            status_after = self._get_network_status()
            self.logger.info(f"Tamanho do cache DNS após a limpeza: {status_after['dns_cache_size']} entradas")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar cache DNS: {e}")
            return False
    
    def full_network_reset(self) -> bool:
        """
        Executa o reset completo da rede.
        Executa todos os comandos de reset em sequência:
        1. Liberação de IP
        2. Reset do Winsock
        3. Reset das configurações IP
        4. Renovação de IP
        5. Limpeza do cache DNS
        
        Returns:
            bool: True se todas as operações foram bem-sucedidas
        """
        self.logger.info("Iniciando reset completo da rede")
        
        try:
            # Obter status antes
            status_before = self._get_network_status()
            self.logger.info(f"Status inicial: {len(status_before['adapters'])} adaptadores ativos")
            
            # Executar comandos em sequência
            steps = [
                ('release', self.release_ip_configuration),
                ('winsock', self.reset_winsock),
                ('ip', self.reset_ip_configuration),
                ('renew', self.renew_ip_configuration),
                ('flushdns', self.flush_dns_cache)
            ]
            
            success_count = 0
            total_steps = len(steps)
            
            for step_name, step_function in steps:
                self.logger.info(f"Executando etapa {step_name} ({success_count+1}/{total_steps})")
                
                try:
                    if step_function():
                        success_count += 1
                        self.logger.info(f"Etapa {step_name} concluída com sucesso")
                    else:
                        self.logger.error(f"Etapa {step_name} falhou")
                except Exception as e:
                    self.logger.error(f"Erro na etapa {step_name}: {e}")
            
            # Obter status depois
            status_after = self._get_network_status()
            self.logger.info(f"Status final: {len(status_after['adapters'])} adaptadores ativos")
            
            # Verificar resultado
            all_successful = success_count == total_steps
            self.logger.info(f"Reset completo concluído: {success_count}/{total_steps} etapas bem-sucedidas")
            
            if all_successful:
                self.logger.info("Reset completo da rede concluído com sucesso!")
            else:
                self.logger.warning(f"Reset completo da rede concluído com {total_steps - success_count} falhas")
            
            return all_successful
            
        except Exception as e:
            self.logger.error(f"Erro durante o reset completo da rede: {e}")
            return False
    
    def check_network_status(self) -> Dict:
        """
        Verifica o status atual da rede.
        
        Returns:
            Dict: Status detalhado da rede
        """
        self.logger.info("Verificando status da rede")
        return self._get_network_status()
    
    def __del__(self):
        """Limpeza ao destruir o objeto."""
        try:
            pythoncom.CoUninitialize()
        except:
            pass


# Funções de conveniência para uso direto
def reset_winsock():
    """Executa o reset completo do Winsock."""
    manager = NetworkResetManager()
    return manager.reset_winsock()


def reset_ip_configuration():
    """Executa o reset das configurações IP."""
    manager = NetworkResetManager()
    return manager.reset_ip_configuration()


def release_ip_configuration():
    """Libera as configurações IP atuais."""
    manager = NetworkResetManager()
    return manager.release_ip_configuration()


def renew_ip_configuration():
    """Renova as configurações IP."""
    manager = NetworkResetManager()
    return manager.renew_ip_configuration()


def flush_dns_cache():
    """Limpa o cache DNS."""
    manager = NetworkResetManager()
    return manager.flush_dns_cache()


def full_network_reset():
    """Executa o reset completo da rede."""
    manager = NetworkResetManager()
    return manager.full_network_reset()


def check_network_status():
    """Verifica o status atual da rede."""
    manager = NetworkResetManager()
    return manager.check_network_status()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação de Reset de Rede ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = NetworkResetManager()
        
        # Verificar se está rodando como administrador
        if not manager._is_admin():
            print("⚠️  AVISO: Este script requer privilégios de administrador para funcionar corretamente")
            print("   Execute o prompt de comando como administrador e tente novamente")
            print()
        
        # Verificar status atual
        print("1. Status Atual da Rede:")
        status = manager.check_network_status()
        print(f"   Adaptadores ativos: {len(status['adapters'])}")
        print(f"   Tamanho do cache DNS: {status['dns_cache_size']} entradas")
        print(f"   Rotas de rede: {status['routes_count']} rotas")
        print()
        
        # Executar reset completo (comentado para segurança)
        print("2. Reset Completo da Rede:")
        print("   Para executar o reset completo, descomente a linha abaixo:")
        print("   # success = manager.full_network_reset()")
        print("   # if success:")
        print("   #     print('   ✓ Reset completo concluído com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha no reset completo')")
        print()
        
        # Exemplo de comandos individuais (comentados para segurança)
        print("3. Comandos Individuais:")
        print("   Para executar comandos individuais, descomente as linhas abaixo:")
        print("   # manager.reset_winsock()")
        print("   # manager.flush_dns_cache()")
        print()
        
        print("Operação concluída!")
        print()
        print("💡 DICA: Após executar o reset completo, reinicie o computador para aplicar todas as mudanças")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")