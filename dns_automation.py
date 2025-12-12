#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação de Configurações DNS
========================================

Este módulo automatiza a configuração de servidores DNS no Windows,
essencial para otimizar a conexão com a Blaze e outros serviços.

Funcionalidades:
- Configurar DNS Cloudflare (1.1.1.1 / 1.0.0.1)
- Configurar DNS Google (8.8.8.8 / 8.8.4.4)
- Restaurar DNS automático (DHCP)
- Verificar status atual das configurações DNS
- Backup e restauração de configurações

Autor: Sistema de Automação
Versão: 1.0.0
Data: 2025-12-12
"""

import logging
import os
import sys
import json
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime

# Importações específicas do Windows
try:
    import winreg
    import wmi
    import pythoncom
    from winreg import HKEY_LOCAL_MACHINE, KEY_ALL_ACCESS, KEY_READ, REG_SZ, REG_DWORD
except ImportError as e:
    print("ERRO: Este módulo requer Python para Windows com pywin32 instalado.")
    print("Execute: pip install pywin32 wmi")
    sys.exit(1)


class DNSManager:
    """
    Gerenciador de Configurações DNS para Automação
    
    Esta classe fornece métodos para configurar, verificar e gerenciar
    as configurações de servidores DNS dos adaptadores de rede.
    """
    
    # Servidores DNS pré-definidos
    DNS_SERVERS = {
        'cloudflare': {
            'name': 'Cloudflare',
            'primary': '1.1.1.1',
            'secondary': '1.0.0.1',
            'description': 'DNS rápido e seguro para WebSocket'
        },
        'google': {
            'name': 'Google Public DNS',
            'primary': '8.8.8.8',
            'secondary': '8.8.4.4',
            'description': 'DNS público do Google'
        },
        'opendns': {
            'name': 'OpenDNS',
            'primary': '208.67.222.222',
            'secondary': '208.67.220.220',
            'description': 'DNS com filtragem de conteúdo'
        },
        'quad9': {
            'name': 'Quad9',
            'primary': '9.9.9.9',
            'secondary': '149.112.112.112',
            'description': 'DNS seguro e privado'
        }
    }
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de DNS.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando DNSManager")
        
        # Inicializar WMI
        try:
            pythoncom.CoInitialize()
            self.wmi = wmi.WMI()
            self.logger.info("WMI inicializado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar WMI: {e}")
            raise
        
        # Caminho do registro para configurações de rede
        self.NETWORK_REGISTRY_PATH = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        self.BACKUP_FILE = "dns_backup.json"
        
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('dns_automation.log', encoding='utf-8')
            ]
        )
    
    def detect_network_adapters(self) -> List[Dict]:
        """
        Detecta todos os adaptadores de rede disponíveis no sistema.
        
        Returns:
            List[Dict]: Lista de adaptadores com informações detalhadas
        """
        self.logger.info("Iniciando detecção de adaptadores de rede")
        adapters = []
        
        try:
            # Buscar adaptadores via WMI
            for nic in self.wmi.Win32_NetworkAdapter():
                if nic.NetConnectionID and nic.NetConnectionStatus in [1, 2]:  # Conectado ou desconectado
                    adapter_info = {
                        'name': nic.NetConnectionID,
                        'device_id': nic.DeviceID,
                        'adapter_type': nic.AdapterType,
                        'mac_address': nic.MACAddress,
                        'speed': nic.Speed,
                        'status': 'Conectado' if nic.NetConnectionStatus == 2 else 'Desconectado',
                        'manufacturer': nic.Manufacturer,
                        'description': nic.Description,
                        'registry_path': self._get_adapter_registry_path(nic.NetConnectionID, nic.DeviceID)
                    }
                    adapters.append(adapter_info)
                    self.logger.info(f"Adaptador detectado: {nic.NetConnectionID}")
            
            self.logger.info(f"Total de adaptadores detectados: {len(adapters)}")
            return adapters
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar adaptadores: {e}")
            raise
    
    def _get_adapter_registry_path(self, adapter_name: str, device_id: str) -> Optional[str]:
        """
        Obtém o caminho do registro para um adaptador específico usando múltiplas estratégias.
        
        Args:
            adapter_name (str): Nome do adaptador
            device_id (str): ID do dispositivo do adaptador
            
        Returns:
            Optional[str]: Caminho do registro ou None se não encontrado
        """
        self.logger.info(f"Procurando caminho do registro para adaptador: {adapter_name} (ID: {device_id})")
        
        # Estratégia 1: Tentar encontrar via WMI e mapear para registro
        try:
            # Buscar adaptadores e tentar encontrar correspondência
            for nic in self.wmi.Win32_NetworkAdapter():
                if nic.NetConnectionID == adapter_name and nic.DeviceID == device_id:
                    # Tentar diferentes caminhos baseados no tipo de adaptador
                    base_paths = [
                        r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
                        r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
                    ]
                    
                    for base_path in base_paths:
                        # Tentar com device_id direto
                        test_path = f"{base_path}\\{device_id}"
                        try:
                            with winreg.OpenKey(HKEY_LOCAL_MACHINE, test_path, 0, winreg.KEY_READ):
                                self.logger.info(f"Caminho encontrado: {test_path}")
                                return test_path
                        except:
                            pass
                        
                        # Tentar com device_id entre chaves
                        test_path = f"{base_path}\\{{{device_id}}}"
                        try:
                            with winreg.OpenKey(HKEY_LOCAL_MACHINE, test_path, 0, winreg.KEY_READ):
                                self.logger.info(f"Caminho encontrado: {test_path}")
                                return test_path
                        except:
                            pass
                        
                        # Tentar com device_id zeropad
                        padded_id = device_id.zfill(4)
                        test_path = f"{base_path}\\{padded_id}"
                        try:
                            with winreg.OpenKey(HKEY_LOCAL_MACHINE, test_path, 0, winreg.KEY_READ):
                                self.logger.info(f"Caminho encontrado: {test_path}")
                                return test_path
                        except:
                            pass
        except Exception as e:
            self.logger.warning(f"Erro ao buscar caminho via WMI: {e}")
        
        # Estratégia 2: Tentar caminhos comuns baseados no nome do adaptador
        common_paths = [
            f"{self.NETWORK_REGISTRY_PATH}\\{device_id}",
            f"{self.NETWORK_REGISTRY_PATH}\\{{{device_id}}}",
            f"SYSTEM\\CurrentControlSet\\Control\\Class\\{{{device_id}}}"
        ]
        
        for path in common_paths:
            try:
                with winreg.OpenKey(HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ):
                    self.logger.info(f"Caminho comum encontrado: {path}")
                    return path
            except:
                continue
        
        self.logger.warning(f"Nenhum caminho de registro encontrado para {adapter_name}")
        return None
    
    def _backup_current_dns(self, adapter_name: str, registry_path: str) -> Dict:
        """
        Faz backup das configurações DNS atuais do adaptador.
        
        Args:
            adapter_name (str): Nome do adaptador
            registry_path (str): Caminho do registro do adaptador
            
        Returns:
            Dict: Configurações DNS atuais
        """
        backup = {
            'adapter_name': adapter_name,
            'timestamp': datetime.now().isoformat(),
            'dns_servers': {},
            'dhcp_enabled': False
        }
        
        try:
            with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, KEY_READ) as key:
                try:
                    # Verificar DNS primário
                    primary_dns, _ = winreg.QueryValueEx(key, "NameServer")
                    backup['dns_servers']['primary'] = primary_dns
                except FileNotFoundError:
                    backup['dns_servers']['primary'] = None
                
                try:
                    # Verificar DNS secundário
                    secondary_dns, _ = winreg.QueryValueEx(key, "DHCPNameServer")
                    backup['dns_servers']['secondary'] = secondary_dns
                except FileNotFoundError:
                    backup['dns_servers']['secondary'] = None
                
                try:
                    # Verificar se DHCP está habilitado
                    dhcp_enabled, _ = winreg.QueryValueEx(key, "EnableDHCP")
                    backup['dhcp_enabled'] = bool(dhcp_enabled)
                except FileNotFoundError:
                    backup['dhcp_enabled'] = False
                    
        except Exception as e:
            self.logger.warning(f"Não foi possível fazer backup do adaptador {adapter_name}: {e}")
            
        return backup
    
    def _save_backup(self, backup_data: List[Dict]) -> bool:
        """
        Salva o backup das configurações DNS em arquivo JSON.
        
        Args:
            backup_data (List[Dict]): Dados do backup
            
        Returns:
            bool: True se salvo com sucesso
        """
        try:
            with open(self.BACKUP_FILE, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Backup salvo em: {self.BACKUP_FILE}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar backup: {e}")
            return False
    
    def _load_backup(self) -> Optional[List[Dict]]:
        """
        Carrega o backup das configurações DNS do arquivo JSON.
        
        Returns:
            Optional[List[Dict]]: Dados do backup ou None se não encontrado
        """
        try:
            if os.path.exists(self.BACKUP_FILE):
                with open(self.BACKUP_FILE, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                self.logger.info(f"Backup carregado de: {self.BACKUP_FILE}")
                return backup_data
        except Exception as e:
            self.logger.error(f"Erro ao carregar backup: {e}")
        return None
    
    def configure_dns(self, dns_type: str = 'cloudflare', adapter_name: Optional[str] = None) -> bool:
        """
        Configura os servidores DNS para o adaptador especificado.
        
        Args:
            dns_type (str): Tipo de DNS ('cloudflare', 'google', 'opendns', 'quad9' ou 'auto')
            adapter_name (str, optional): Nome específico do adaptador para configurar
                                         Se None, aplica para todos os adaptadores conectados
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info(f"Configurando DNS {dns_type} para: {adapter_name or 'todos os adaptadores'}")
        
        if dns_type not in self.DNS_SERVERS and dns_type != 'auto':
            raise ValueError(f"Tipo de DNS '{dns_type}' não suportado. Use: {list(self.DNS_SERVERS.keys())}")
        
        try:
            adapters = self.detect_network_adapters()
            success_count = 0
            total_count = 0
            backup_data = []
            
            # Fazer backup das configurações atuais
            for adapter in adapters:
                if adapter_name and adapter['name'] != adapter_name:
                    continue
                    
                backup = self._backup_current_dns(adapter['name'], adapter['registry_path'])
                backup_data.append(backup)
            
            # Salvar backup
            if backup_data:
                self._save_backup(backup_data)
            
            # Configurar DNS
            for adapter in adapters:
                if adapter_name and adapter['name'] != adapter_name:
                    continue
                    
                total_count += 1
                
                try:
                    registry_path = adapter['registry_path']
                    
                    # Abrir a chave do registro com permissão de escrita
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, KEY_ALL_ACCESS) as key:
                        if dns_type == 'auto':
                            # Restaurar configuração automática (DHCP)
                            winreg.SetValueEx(key, "EnableDHCP", 0, REG_DWORD, 1)
                            winreg.SetValueEx(key, "NameServer", 0, REG_SZ, "")
                            self.logger.info(f"DHCP habilitado para: {adapter['name']}")
                        else:
                            # Configurar DNS específico
                            dns_config = self.DNS_SERVERS[dns_type]
                            
                            # Desabilitar DHCP para DNS manual
                            winreg.SetValueEx(key, "EnableDHCP", 0, REG_DWORD, 0)
                            
                            # Configurar DNS primário
                            winreg.SetValueEx(key, "NameServer", 0, REG_SZ, dns_config['primary'])
                            
                            # Configurar DNS secundário (se disponível)
                            if dns_config['secondary']:
                                winreg.SetValueEx(key, "DomainNameServer", 0, REG_SZ, dns_config['secondary'])
                            
                            self.logger.info(f"DNS {dns_config['name']} configurado para: {adapter['name']}")
                    
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao configurar DNS para {adapter['name']}: {e}")
            
            self.logger.info(f"Operação concluída: {success_count}/{total_count} adaptadores configurados")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar DNS: {e}")
            raise
    
    def restore_dns_backup(self, adapter_name: Optional[str] = None) -> bool:
        """
        Restaura as configurações DNS do backup.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador para restaurar
                                         Se None, restaura para todos os adaptadores
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info(f"Restaurando backup DNS para: {adapter_name or 'todos os adaptadores'}")
        
        backup_data = self._load_backup()
        if not backup_data:
            self.logger.warning("Nenhum backup encontrado para restaurar")
            return False
        
        try:
            success_count = 0
            total_count = 0
            
            for backup in backup_data:
                if adapter_name and backup['adapter_name'] != adapter_name:
                    continue
                    
                total_count += 1
                
                try:
                    # Encontrar o adaptador atual
                    adapters = self.detect_network_adapters()
                    current_adapter = None
                    
                    for adapter in adapters:
                        if adapter['name'] == backup['adapter_name']:
                            current_adapter = adapter
                            break
                    
                    if not current_adapter:
                        self.logger.warning(f"Adaptador {backup['adapter_name']} não encontrado para restauração")
                        continue
                    
                    registry_path = current_adapter['registry_path']
                    
                    # Restaurar configurações
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, KEY_ALL_ACCESS) as key:
                        if backup['dhcp_enabled']:
                            # Restaurar DHCP
                            winreg.SetValueEx(key, "EnableDHCP", 0, REG_DWORD, 1)
                            winreg.SetValueEx(key, "NameServer", 0, REG_SZ, "")
                        else:
                            # Restaurar DNS manual
                            winreg.SetValueEx(key, "EnableDHCP", 0, REG_DWORD, 0)
                            
                            if backup['dns_servers']['primary']:
                                winreg.SetValueEx(key, "NameServer", 0, REG_SZ, backup['dns_servers']['primary'])
                            
                            if backup['dns_servers']['secondary']:
                                winreg.SetValueEx(key, "DomainNameServer", 0, REG_SZ, backup['dns_servers']['secondary'])
                    
                    self.logger.info(f"Backup restaurado para: {backup['adapter_name']}")
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao restaurar backup para {backup['adapter_name']}: {e}")
            
            self.logger.info(f"Restauração concluída: {success_count}/{total_count} adaptadores restaurados")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar backup: {e}")
            raise
    
    def check_dns_status(self, adapter_name: Optional[str] = None) -> Dict:
        """
        Verifica o status atual das configurações DNS.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador para verificar
            
        Returns:
            Dict: Status detalhado das configurações DNS
        """
        self.logger.info(f"Verificando status DNS para: {adapter_name or 'todos os adaptadores'}")
        status_info = {
            'timestamp': datetime.now().isoformat(),
            'adapters': {},
            'summary': {
                'total_adapters': 0,
                'manual_dns': 0,
                'dhcp_enabled': 0,
                'unknown_status': 0
            }
        }
        
        try:
            adapters = self.detect_network_adapters()
            
            for adapter in adapters:
                if adapter_name and adapter['name'] != adapter_name:
                    continue
                    
                adapter_status = {
                    'name': adapter['name'],
                    'device_id': adapter['device_id'],
                    'dns_status': 'unknown',
                    'primary_dns': None,
                    'secondary_dns': None,
                    'dhcp_enabled': False,
                    'dns_type': None
                }
                
                try:
                    registry_path = adapter['registry_path']
                    
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, KEY_READ) as key:
                        try:
                            # Verificar DHCP
                            dhcp_enabled, _ = winreg.QueryValueEx(key, "EnableDHCP")
                            adapter_status['dhcp_enabled'] = bool(dhcp_enabled)
                            
                            if dhcp_enabled:
                                adapter_status['dns_status'] = 'dhcp'
                                adapter_status['dns_type'] = 'Automático (DHCP)'
                            else:
                                adapter_status['dns_status'] = 'manual'
                                
                                # Verificar DNS primário
                                try:
                                    primary_dns, _ = winreg.QueryValueEx(key, "NameServer")
                                    adapter_status['primary_dns'] = primary_dns
                                    
                                    # Identificar tipo de DNS
                                    for dns_key, dns_config in self.DNS_SERVERS.items():
                                        if primary_dns == dns_config['primary']:
                                            adapter_status['dns_type'] = dns_config['name']
                                            break
                                    
                                    if not adapter_status['dns_type']:
                                        adapter_status['dns_type'] = 'DNS Personalizado'
                                        
                                except FileNotFoundError:
                                    adapter_status['primary_dns'] = None
                                
                                # Verificar DNS secundário
                                try:
                                    secondary_dns, _ = winreg.QueryValueEx(key, "DomainNameServer")
                                    adapter_status['secondary_dns'] = secondary_dns
                                except FileNotFoundError:
                                    adapter_status['secondary_dns'] = None
                                    
                        except FileNotFoundError:
                            adapter_status['dns_status'] = 'not_configured'
                            
                except Exception as e:
                    self.logger.warning(f"Não foi possível verificar status DNS do adaptador {adapter['name']}: {e}")
                    adapter_status['dns_status'] = 'error'
                
                status_info['adapters'][adapter['name']] = adapter_status
                
                # Atualizar resumo
                status_info['summary']['total_adapters'] += 1
                if adapter_status['dns_status'] == 'manual':
                    status_info['summary']['manual_dns'] += 1
                elif adapter_status['dns_status'] == 'dhcp':
                    status_info['summary']['dhcp_enabled'] += 1
                else:
                    status_info['summary']['unknown_status'] += 1
            
            self.logger.info("Verificação de status DNS concluída")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status DNS: {e}")
            raise
    
    def set_cloudflare_dns(self, adapter_name: Optional[str] = None) -> bool:
        """
        Configura DNS Cloudflare (1.1.1.1 / 1.0.0.1) para o adaptador.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        return self.configure_dns('cloudflare', adapter_name)
    
    def set_google_dns(self, adapter_name: Optional[str] = None) -> bool:
        """
        Configura DNS Google (8.8.8.8 / 8.8.4.4) para o adaptador.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        return self.configure_dns('google', adapter_name)
    
    def set_auto_dns(self, adapter_name: Optional[str] = None) -> bool:
        """
        Restaura configuração automática de DNS (DHCP) para o adaptador.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        return self.configure_dns('auto', adapter_name)
    
    def list_available_dns(self) -> Dict:
        """
        Lista todos os tipos de DNS disponíveis.
        
        Returns:
            Dict: Dicionário com informações dos DNS disponíveis
        """
        return self.DNS_SERVERS.copy()
    
    def list_network_adapters(self) -> List[str]:
        """
        Lista apenas os nomes dos adaptadores disponíveis.
        
        Returns:
            List[str]: Lista de nomes dos adaptadores
        """
        self.logger.info("Listando adaptadores disponíveis")
        
        try:
            adapters = self.detect_network_adapters()
            adapter_names = [adapter['name'] for adapter in adapters]
            
            self.logger.info(f"Adaptadores encontrados: {adapter_names}")
            return adapter_names
            
        except Exception as e:
            self.logger.error(f"Erro ao listar adaptadores: {e}")
            raise
    
    def __del__(self):
        """Limpeza ao destruir o objeto."""
        try:
            pythoncom.CoUninitialize()
        except:
            pass


# Funções de conveniência para uso direto
def set_cloudflare_dns(adapter_name: Optional[str] = None):
    """Configura DNS Cloudflare para todos os adaptadores ou adaptador específico."""
    manager = DNSManager()
    return manager.set_cloudflare_dns(adapter_name)


def set_google_dns(adapter_name: Optional[str] = None):
    """Configura DNS Google para todos os adaptadores ou adaptador específico."""
    manager = DNSManager()
    return manager.set_google_dns(adapter_name)


def set_auto_dns(adapter_name: Optional[str] = None):
    """Restaura DNS automático (DHCP) para todos os adaptadores ou adaptador específico."""
    manager = DNSManager()
    return manager.set_auto_dns(adapter_name)


def check_dns_status(adapter_name: Optional[str] = None):
    """Verifica o status DNS de todos os adaptadores ou adaptador específico."""
    manager = DNSManager()
    return manager.check_dns_status(adapter_name)


def list_network_adapters():
    """Lista todos os adaptadores de rede disponíveis."""
    manager = DNSManager()
    return manager.list_network_adapters()


def restore_dns_backup(adapter_name: Optional[str] = None):
    """Restaura as configurações DNS do backup."""
    manager = DNSManager()
    return manager.restore_dns_backup(adapter_name)


def list_available_dns():
    """Lista todos os tipos de DNS disponíveis."""
    manager = DNSManager()
    return manager.list_available_dns()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação de Configurações DNS ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = DNSManager()
        
        # Listar adaptadores disponíveis
        print("1. Adaptadores de Rede Disponíveis:")
        adapters = manager.list_network_adapters()
        for i, adapter in enumerate(adapters, 1):
            print(f"   {i}. {adapter}")
        print()
        
        # Verificar status atual
        print("2. Status Atual das Configurações DNS:")
        status = manager.check_dns_status()
        for adapter_name, adapter_status in status['adapters'].items():
            print(f"   {adapter_name}:")
            print(f"     Status: {adapter_status['dns_status']}")
            print(f"     Tipo: {adapter_status['dns_type']}")
            print(f"     DNS Primário: {adapter_status['primary_dns']}")
            print(f"     DNS Secundário: {adapter_status['secondary_dns']}")
            print(f"     DHCP: {'Habilitado' if adapter_status['dhcp_enabled'] else 'Desabilitado'}")
        print()
        
        # Configurar DNS Cloudflare
        print("3. Configurando DNS Cloudflare...")
        success = manager.set_cloudflare_dns()
        if success:
            print("   [OK] DNS Cloudflare configurado com sucesso!")
        else:
            print("   [ERRO] Falha ao configurar DNS Cloudflare")
        print()
        
        # Verificar novo status
        print("4. Novo Status (após configuração Cloudflare):")
        new_status = manager.check_dns_status()
        for adapter_name, adapter_status in new_status['adapters'].items():
            print(f"   {adapter_name}: {adapter_status['dns_type']}")
        print()
        
        print("Operação concluída!")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")