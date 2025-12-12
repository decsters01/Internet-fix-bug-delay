#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação do Sistema
==============================

Este módulo automatiza a otimização do sistema Windows para melhorar o desempenho
durante a execução de aplicações críticas como robôs de trading.

Funcionalidades:
- Desabilitar permanentemente o Windows Update
- Fechar aplicativos de sincronização/streaming da bandeja do sistema
- Eliminação de ruído de fundo do sistema
- Otimização de cache e rede
- Backup e restauração das configurações originais
- Verificação de status do sistema
- Validação de privilégios de administrador

Autor: Sistema de Automação
Versão: 1.0.0
Data: 2025-12-12
"""

import logging
import os
import sys
import json
import subprocess
import psutil
import time
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


class SystemAutomationManager:
    """
    Gerenciador de Automação do Sistema para Otimização
    
    Esta classe fornece métodos para otimizar o sistema Windows,
    desabilitando atualizações, fechando aplicativos e eliminando
    ruídos de fundo que possam afetar o desempenho.
    """
    
    # Aplicativos da bandeja do sistema a serem fechados
    TRAY_APPLICATIONS = [
        'steam.exe',
        'steamwebhelper.exe',
        'epicgameslauncher.exe',
        'onedrive.exe',
        'googledrivesync.exe',
        'dropbox.exe',
        'utorrent.exe',
        'bit torrent.exe',
        'qbittorrent.exe'
    ]
    
    # Serviços que podem causar ruído de fundo
    BACKGROUND_SERVICES = [
        'wuauserv',           # Windows Update
        'UsoSvc',             # Serviço de Orquestração de Atualização
        'dosvc',              # Serviço de Otimização de Entrega
        'BITS'                # Serviço de Transferência Inteligente em Segundo Plano
    ]
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de automação do sistema.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando SystemAutomationManager")
        
        # Verificar se está rodando como administrador
        if not self._is_admin():
            self.logger.warning("Este módulo requer privilégios de administrador para funcionar corretamente")
        
        # Arquivo de backup para configurações originais
        self.backup_file = Path("system_automation_backup.json")
        
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('system_automation.log', encoding='utf-8')
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
        Faz backup das configurações do sistema atuais.
        
        Returns:
            Dict: Configurações do sistema atuais
        """
        backup = {
            'timestamp': datetime.now().isoformat(),
            'settings': {},
            'services': {}
        }
        
        self.logger.info("Fazendo backup das configurações do sistema atuais")
        
        try:
            # Backup de configurações do Windows Update
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU", 0, KEY_READ) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, "NoAutoUpdate")
                    backup['settings']['NoAutoUpdate'] = value
                except FileNotFoundError:
                    backup['settings']['NoAutoUpdate'] = None
                    
            # Backup de serviços
            for service in self.BACKGROUND_SERVICES:
                try:
                    result = subprocess.run(['sc', 'query', service], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        backup['services'][service] = 'enabled'
                    else:
                        backup['services'][service] = 'disabled'
                except Exception as e:
                    self.logger.warning(f"Não foi possível verificar o status do serviço {service}: {e}")
                    backup['services'][service] = 'unknown'
                        
        except Exception as e:
            self.logger.error(f"Erro ao fazer backup das configurações: {e}")
            
        return backup
    
    def _save_backup(self, backup_data: Dict) -> bool:
        """
        Salva o backup das configurações do sistema em arquivo JSON.
        
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
        Carrega o backup das configurações do sistema do arquivo JSON.
        
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
    
    def disable_windows_update(self) -> bool:
        """
        Desabilita permanentemente o Windows Update.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Desabilitando Windows Update permanentemente")
        
        try:
            # Fazer backup antes da alteração
            backup_data = self._backup_current_settings()
            if not self._save_backup(backup_data):
                self.logger.warning("Falha no backup, continuando sem backup")
            
            # Criar chave de política se não existir
            try:
                with winreg.CreateKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate") as key:
                    pass
                with winreg.CreateKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU") as key:
                    pass
            except Exception as e:
                self.logger.error(f"Erro ao criar chaves de registro: {e}")
                return False
            
            # Desabilitar Windows Update
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU", 0, KEY_ALL_ACCESS) as key:
                # Desabilitar atualizações automáticas
                winreg.SetValueEx(key, "NoAutoUpdate", 0, REG_DWORD, 1)
                self.logger.info("Windows Update desabilitado: NoAutoUpdate = 1")
                
                # Configurar opções adicionais
                winreg.SetValueEx(key, "AUOptions", 0, REG_DWORD, 1)
                winreg.SetValueEx(key, "ScheduledInstallDay", 0, REG_DWORD, 0)
                winreg.SetValueEx(key, "ScheduledInstallTime", 0, REG_DWORD, 3)
                
            # Parar e desabilitar serviços do Windows Update
            services_disabled = 0
            for service in ['wuauserv', 'UsoSvc', 'dosvc', 'BITS']:
                try:
                    # Parar o serviço
                    subprocess.run(['net', 'stop', service], 
                                 capture_output=True, text=True, timeout=30)
                    self.logger.info(f"Serviço {service} parado")
                    
                    # Desabilitar o serviço
                    subprocess.run(['sc', 'config', service, 'start=', 'disabled'], 
                                 capture_output=True, text=True, timeout=30)
                    self.logger.info(f"Serviço {service} desabilitado")
                    services_disabled += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao gerenciar serviço {service}: {e}")
            
            self.logger.info(f"Windows Update desabilitado com sucesso. {services_disabled} serviços afetados")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao desabilitar Windows Update: {e}")
            return False
    
    def close_tray_applications(self) -> bool:
        """
        Fecha aplicativos de sincronização/streaming da bandeja do sistema.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Fechando aplicativos da bandeja do sistema")
        
        try:
            closed_count = 0
            
            # Listar todos os processos em execução
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    process_name = proc.info['name'].lower()
                    if process_name in self.TRAY_APPLICATIONS:
                        # Fechar processo
                        proc = psutil.Process(proc.info['pid'])
                        proc.terminate()
                        proc.wait(timeout=10)  # Esperar até 10 segundos
                        self.logger.info(f"Aplicativo fechado: {process_name}")
                        closed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    # Processo já terminado ou sem permissão
                    pass
                except Exception as e:
                    self.logger.warning(f"Erro ao fechar processo {process_name}: {e}")
            
            self.logger.info(f"Aplicativos da bandeja fechados: {closed_count}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao fechar aplicativos da bandeja: {e}")
            return False
    
    def disable_background_services(self) -> bool:
        """
        Desabilita serviços em segundo plano que causam ruído.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Desabilitando serviços em segundo plano")
        
        try:
            disabled_count = 0
            
            for service in self.BACKGROUND_SERVICES:
                try:
                    # Parar o serviço
                    subprocess.run(['net', 'stop', service], 
                                 capture_output=True, text=True, timeout=30)
                    self.logger.info(f"Serviço {service} parado")
                    
                    # Desabilitar o serviço
                    subprocess.run(['sc', 'config', service, 'start=', 'disabled'], 
                                 capture_output=True, text=True, timeout=30)
                    self.logger.info(f"Serviço {service} desabilitado")
                    disabled_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Erro ao gerenciar serviço {service}: {e}")
            
            self.logger.info(f"Serviços em segundo plano desabilitados: {disabled_count}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao desabilitar serviços em segundo plano: {e}")
            return False
    
    def clear_system_cache(self) -> bool:
        """
        Limpa o cache do sistema para liberar memória.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Limpando cache do sistema")
        
        try:
            # Limpar cache DNS
            subprocess.run(['ipconfig', '/flushdns'], 
                         capture_output=True, text=True, timeout=30)
            self.logger.info("Cache DNS limpo")
            
            # Limpar cache temporário
            temp_dirs = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                r'C:\Windows\Temp'
            ]
            
            cleaned_files = 0
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        for filename in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, filename)
                            try:
                                if os.path.isfile(file_path):
                                    os.unlink(file_path)
                                    cleaned_files += 1
                                elif os.path.isdir(file_path):
                                    import shutil
                                    shutil.rmtree(file_path)
                                    cleaned_files += 1
                            except Exception:
                                pass  # Ignorar arquivos em uso
                    except Exception as e:
                        self.logger.warning(f"Erro ao limpar diretório {temp_dir}: {e}")
            
            self.logger.info(f"Cache do sistema limpo: {cleaned_files} arquivos removidos")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar cache do sistema: {e}")
            return False
    
    def optimize_network_settings(self) -> bool:
        """
        Otimiza configurações de rede para melhor desempenho.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Otimizando configurações de rede")
        
        try:
            # Configurações de registro para otimização de rede
            network_settings = {
                r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters": {
                    "TcpTimedWaitDelay": 30,
                    "MaxUserPort": 65534,
                    "TcpMaxDataRetransmissions": 3,
                    "DefaultTTL": 64
                },
                r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces": {
                    # Configurações específicas por interface serão aplicadas dinamicamente
                }
            }
            
            optimized_count = 0
            
            for reg_path, settings in network_settings.items():
                if not settings:  # Pular se não houver configurações
                    continue
                    
                try:
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, reg_path, 0, KEY_ALL_ACCESS) as key:
                        for setting_name, setting_value in settings.items():
                            winreg.SetValueEx(key, setting_name, 0, REG_DWORD, setting_value)
                            self.logger.info(f"Configuração de rede aplicada: {setting_name} = {setting_value}")
                            optimized_count += 1
                except Exception as e:
                    self.logger.warning(f"Erro ao aplicar configurações em {reg_path}: {e}")
            
            self.logger.info(f"Configurações de rede otimizadas: {optimized_count} parâmetros")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao otimizar configurações de rede: {e}")
            return False
    
    def system_cleanup(self) -> bool:
        """
        Realiza uma limpeza completa do sistema (eliminação de ruído de fundo).
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando limpeza completa do sistema")
        
        try:
            # Fechar aplicativos da bandeja
            self.close_tray_applications()
            
            # Desabilitar serviços em segundo plano
            self.disable_background_services()
            
            # Limpar cache do sistema
            self.clear_system_cache()
            
            # Otimizar configurações de rede
            self.optimize_network_settings()
            
            self.logger.info("Limpeza completa do sistema concluída")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na limpeza completa do sistema: {e}")
            return False
    
    def restore_original_settings(self) -> bool:
        """
        Restaura as configurações originais do sistema a partir do backup.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando restauração das configurações originais do sistema")
        
        backup_data = self._load_backup()
        if not backup_data:
            self.logger.error("Nenhum backup encontrado para restaurar")
            return False
        
        try:
            restored_count = 0
            
            # Restaurar configurações do Windows Update
            if 'settings' in backup_data:
                try:
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU", 0, KEY_ALL_ACCESS) as key:
                        no_auto_update = backup_data['settings'].get('NoAutoUpdate')
                        if no_auto_update is not None:
                            winreg.SetValueEx(key, "NoAutoUpdate", 0, REG_DWORD, no_auto_update)
                            self.logger.info(f"Configuração NoAutoUpdate restaurada: {no_auto_update}")
                            restored_count += 1
                        else:
                            # Remover a configuração se não existia originalmente
                            try:
                                winreg.DeleteValue(key, "NoAutoUpdate")
                                self.logger.info("Configuração NoAutoUpdate removida")
                                restored_count += 1
                            except FileNotFoundError:
                                pass
                except Exception as e:
                    self.logger.warning(f"Erro ao restaurar configurações do Windows Update: {e}")
            
            # Restaurar serviços
            if 'services' in backup_data:
                for service, status in backup_data['services'].items():
                    try:
                        if status == 'enabled':
                            # Habilitar o serviço
                            subprocess.run(['sc', 'config', service, 'start=', 'auto'], 
                                         capture_output=True, text=True, timeout=30)
                            self.logger.info(f"Serviço {service} reabilitado")
                            restored_count += 1
                        elif status == 'disabled':
                            # Manter desabilitado (já estava desabilitado)
                            self.logger.info(f"Serviço {service} mantido desabilitado")
                            restored_count += 1
                    except Exception as e:
                        self.logger.warning(f"Erro ao restaurar serviço {service}: {e}")
            
            self.logger.info(f"Restauração concluída: {restored_count} configurações restauradas")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar configurações: {e}")
            return False
    
    def check_system_status(self) -> Dict:
        """
        Verifica o status atual do sistema otimizado.
        
        Returns:
            Dict: Status detalhado do sistema
        """
        self.logger.info("Verificando status do sistema")
        
        status_info = {
            'timestamp': datetime.now().isoformat(),
            'windows_update': {
                'disabled': False,
                'services_status': {}
            },
            'tray_applications': {
                'running': [],
                'closed': []
            },
            'background_services': {
                'disabled': [],
                'running': []
            },
            'cache_status': 'unknown',
            'network_optimized': False
        }
        
        try:
            # Verificar status do Windows Update
            try:
                with winreg.OpenKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU", 0, KEY_READ) as key:
                    value, _ = winreg.QueryValueEx(key, "NoAutoUpdate")
                    status_info['windows_update']['disabled'] = (value == 1)
            except FileNotFoundError:
                status_info['windows_update']['disabled'] = False
            
            # Verificar status dos serviços
            for service in ['wuauserv', 'UsoSvc', 'dosvc', 'BITS']:
                try:
                    result = subprocess.run(['sc', 'query', service], 
                                          capture_output=True, text=True, timeout=10)
                    if 'RUNNING' in result.stdout:
                        status_info['windows_update']['services_status'][service] = 'running'
                    elif 'STOPPED' in result.stdout:
                        status_info['windows_update']['services_status'][service] = 'stopped'
                    else:
                        status_info['windows_update']['services_status'][service] = 'disabled'
                except Exception:
                    status_info['windows_update']['services_status'][service] = 'unknown'
            
            # Verificar aplicativos da bandeja em execução
            running_apps = []
            for proc in psutil.process_iter(['name']):
                try:
                    process_name = proc.info['name'].lower()
                    if process_name in self.TRAY_APPLICATIONS:
                        running_apps.append(process_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            status_info['tray_applications']['running'] = running_apps
            status_info['tray_applications']['closed'] = [app for app in self.TRAY_APPLICATIONS if app not in running_apps]
            
            # Verificar serviços em segundo plano
            for service in self.BACKGROUND_SERVICES:
                try:
                    result = subprocess.run(['sc', 'query', service], 
                                          capture_output=True, text=True, timeout=10)
                    if 'RUNNING' in result.stdout:
                        status_info['background_services']['running'].append(service)
                    else:
                        status_info['background_services']['disabled'].append(service)
                except Exception:
                    status_info['background_services']['disabled'].append(service)
            
            self.logger.info("Verificação de status do sistema concluída")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status do sistema: {e}")
            return status_info
    
    def full_system_optimization(self) -> bool:
        """
        Realiza uma otimização completa do sistema.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando otimização completa do sistema")
        
        try:
            # Fazer backup antes da otimização
            backup_data = self._backup_current_settings()
            self._save_backup(backup_data)
            
            # Desabilitar Windows Update
            self.disable_windows_update()
            
            # Fechar aplicativos da bandeja
            self.close_tray_applications()
            
            # Desabilitar serviços em segundo plano
            self.disable_background_services()
            
            # Limpar cache do sistema
            self.clear_system_cache()
            
            # Otimizar configurações de rede
            self.optimize_network_settings()
            
            self.logger.info("Otimização completa do sistema concluída")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na otimização completa do sistema: {e}")
            return False
    
    def __del__(self):
        """Limpeza ao destruir o objeto."""
        pass


# Funções de conveniência para uso direto
def disable_windows_update():
    """Desabilita permanentemente o Windows Update."""
    manager = SystemAutomationManager()
    return manager.disable_windows_update()


def close_tray_applications():
    """Fecha aplicativos da bandeja do sistema."""
    manager = SystemAutomationManager()
    return manager.close_tray_applications()


def system_cleanup():
    """Realiza uma limpeza completa do sistema."""
    manager = SystemAutomationManager()
    return manager.system_cleanup()


def full_system_optimization():
    """Realiza uma otimização completa do sistema."""
    manager = SystemAutomationManager()
    return manager.full_system_optimization()


def restore_system_settings():
    """Restaura as configurações originais do sistema."""
    manager = SystemAutomationManager()
    return manager.restore_original_settings()


def check_system_status():
    """Verifica o status atual do sistema."""
    manager = SystemAutomationManager()
    return manager.check_system_status()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação do Sistema ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = SystemAutomationManager()
        
        # Verificar se está rodando como administrador
        if not manager._is_admin():
            print("⚠️  AVISO: Este script requer privilégios de administrador para funcionar corretamente")
            print("   Execute o prompt de comando como administrador e tente novamente")
            print()
        
        # Mostrar status atual do sistema
        print("1. Status Atual do Sistema:")
        status = manager.check_system_status()
        print(f"   Windows Update desabilitado: {status['windows_update']['disabled']}")
        print(f"   Aplicativos da bandeja em execução: {len(status['tray_applications']['running'])}")
        print(f"   Serviços em segundo plano desabilitados: {len(status['background_services']['disabled'])}")
        print()
        
        # Exemplo de otimização (comentado para segurança)
        print("2. Exemplo de Otimização:")
        print("   Para otimizar completamente o sistema, descomente abaixo:")
        print("   # success = manager.full_system_optimization()")
        print("   # if success:")
        print("   #     print('   ✓ Sistema otimizado com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha na otimização do sistema')")
        print()
        
        # Exemplo de backup/restauração
        print("3. Backup e Restauração:")
        print("   Para fazer backup das configurações atuais:")
        print("   # backup_data = manager._backup_current_settings()")
        print("   # manager._save_backup(backup_data)")
        print("   Para restaurar configurações originais:")
        print("   # manager.restore_original_settings()")
        print()
        
        print("Operação concluída!")
        print()
        print("💡 DICA: Execute este módulo como administrador para melhores resultados")
        print("💡 DICA: As otimizações terão efeito imediato")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")