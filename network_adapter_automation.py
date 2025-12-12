#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação de Adaptadores de Rede
==========================================

Este módulo automatiza a desativação da economia de energia dos adaptadores de rede
no Windows, essencial para robôs de alta frequência que não podem ter interrupções
na conexão de rede.

Autor: Sistema de Automação
Versão: 1.0.0
Data: 2025-12-12
"""

import logging
import os
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Importações específicas do Windows
try:
    import winreg
    import wmi
    import pythoncom
    from winreg import HKEY_LOCAL_MACHINE, KEY_ALL_ACCESS, REG_DWORD
except ImportError as e:
    print("ERRO: Este módulo requer Python para Windows com pywin32 instalado.")
    print("Execute: pip install pywin32 wmi")
    sys.exit(1)


class NetworkAdapterManager:
    """
    Gerenciador de Adaptadores de Rede para Automação
    
    Esta classe fornece métodos para detectar, configurar e gerenciar
    as configurações de economia de energia dos adaptadores de rede.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de adaptadores de rede.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando NetworkAdapterManager")
        
        # Inicializar WMI
        try:
            pythoncom.CoInitialize()
            self.wmi = wmi.WMI()
            self.logger.info("WMI inicializado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar WMI: {e}")
            raise
        
        # Caminho do registro para configurações de energia
        self.POWER_REGISTRY_PATH = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
        self.POWER_SETTINGS_KEY = "PnPCapabilities"
        
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('network_adapter_automation.log', encoding='utf-8')
            ]
        )
    
    def detect_adapters(self) -> List[Dict]:
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
                        'description': nic.Description
                    }
                    adapters.append(adapter_info)
                    self.logger.info(f"Adaptador detectado: {nic.NetConnectionID}")
            
            self.logger.info(f"Total de adaptadores detectados: {len(adapters)}")
            return adapters
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar adaptadores: {e}")
            raise
    
    def _get_adapter_registry_path(self, device_id: str) -> str:
        """
        Obtém o caminho do registro para um adaptador específico.
        
        Args:
            device_id (str): ID do dispositivo do adaptador
            
        Returns:
            str: Caminho do registro
        """
        return f"{self.POWER_REGISTRY_PATH}\\{device_id.zfill(4)}"
    
    def check_power_status(self, adapter_name: Optional[str] = None) -> Dict:
        """
        Verifica o status atual da economia de energia dos adaptadores.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador para verificar
            
        Returns:
            Dict: Status detalhado dos adaptadores
        """
        self.logger.info(f"Verificando status de economia de energia para: {adapter_name or 'todos os adaptadores'}")
        status_info = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'adapters': {},
            'summary': {
                'total_adapters': 0,
                'power_saving_enabled': 0,
                'power_saving_disabled': 0,
                'unknown_status': 0
            }
        }
        
        try:
            adapters = self.detect_adapters()
            
            for adapter in adapters:
                if adapter_name and adapter['name'] != adapter_name:
                    continue
                    
                adapter_status = {
                    'name': adapter['name'],
                    'device_id': adapter['device_id'],
                    'current_status': 'unknown',
                    'registry_path': None,
                    'power_setting_value': None,
                    'can_modify': False
                }
                
                try:
                    # Tentar acessar as configurações do registro
                    registry_path = self._get_adapter_registry_path(adapter['device_id'])
                    adapter_status['registry_path'] = registry_path
                    
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_READ) as key:
                        try:
                            value, _ = winreg.QueryValueEx(key, self.POWER_SETTINGS_KEY)
                            adapter_status['power_setting_value'] = value
                            adapter_status['current_status'] = 'power_saving_disabled' if value == 0 else 'power_saving_enabled'
                            adapter_status['can_modify'] = True
                        except FileNotFoundError:
                            adapter_status['current_status'] = 'not_configured'
                            adapter_status['can_modify'] = True
                            
                except Exception as e:
                    self.logger.warning(f"Não foi possível verificar status do adaptador {adapter['name']}: {e}")
                    adapter_status['current_status'] = 'error'
                
                status_info['adapters'][adapter['name']] = adapter_status
                
                # Atualizar resumo
                status_info['summary']['total_adapters'] += 1
                if adapter_status['current_status'] == 'power_saving_enabled':
                    status_info['summary']['power_saving_enabled'] += 1
                elif adapter_status['current_status'] == 'power_saving_disabled':
                    status_info['summary']['power_saving_disabled'] += 1
                else:
                    status_info['summary']['unknown_status'] += 1
            
            self.logger.info("Verificação de status concluída")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status de energia: {e}")
            raise
    
    def disable_power_saving(self, adapter_name: Optional[str] = None) -> bool:
        """
        Desativa a economia de energia dos adaptadores de rede.
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador para configurar
                                         Se None, aplica para todos os adaptadores
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info(f"Desativando economia de energia para: {adapter_name or 'todos os adaptadores'}")
        
        try:
            adapters = self.detect_adapters()
            success_count = 0
            total_count = 0
            
            for adapter in adapters:
                if adapter_name and adapter['name'] != adapter_name:
                    continue
                    
                total_count += 1
                
                try:
                    registry_path = self._get_adapter_registry_path(adapter['device_id'])
                    
                    # Abrir a chave do registro com permissão de escrita
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, KEY_ALL_ACCESS) as key:
                        # Definir o valor para desativar a economia de energia
                        # Valor 0 = Desabilitar economia de energia
                        winreg.SetValueEx(key, self.POWER_SETTINGS_KEY, 0, REG_DWORD, 0)
                        
                    self.logger.info(f"Economia de energia desativada para: {adapter['name']}")
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao desativar economia de energia para {adapter['name']}: {e}")
            
            self.logger.info(f"Operação concluída: {success_count}/{total_count} adaptadores configurados")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao desativar economia de energia: {e}")
            raise
    
    def enable_power_saving(self, adapter_name: Optional[str] = None) -> bool:
        """
        Reativa a economia de energia dos adaptadores de rede (rollback).
        
        Args:
            adapter_name (str, optional): Nome específico do adaptador para configurar
                                         Se None, aplica para todos os adaptadores
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info(f"Reativando economia de energia para: {adapter_name or 'todos os adaptadores'}")
        
        try:
            adapters = self.detect_adapters()
            success_count = 0
            total_count = 0
            
            for adapter in adapters:
                if adapter_name and adapter['name'] != adapter_name:
                    continue
                    
                total_count += 1
                
                try:
                    registry_path = self._get_adapter_registry_path(adapter['device_id'])
                    
                    # Abrir a chave do registro com permissão de escrita
                    with winreg.OpenKey(HKEY_LOCAL_MACHINE, registry_path, 0, KEY_ALL_ACCESS) as key:
                        # Definir o valor padrão para reativar a economia de energia
                        # Remover a chave para restaurar comportamento padrão
                        try:
                            winreg.DeleteValue(key, self.POWER_SETTINGS_KEY)
                        except FileNotFoundError:
                            # A chave já não existe, está OK
                            pass
                        
                    self.logger.info(f"Economia de energia reativada para: {adapter['name']}")
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao reativar economia de energia para {adapter['name']}: {e}")
            
            self.logger.info(f"Rollback concluído: {success_count}/{total_count} adaptadores restaurados")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Erro ao reativar economia de energia: {e}")
            raise
    
    def get_adapter_info(self, adapter_name: str) -> Dict:
        """
        Obtém informações detalhadas de um adaptador específico.
        
        Args:
            adapter_name (str): Nome do adaptador
            
        Returns:
            Dict: Informações detalhadas do adaptador
        """
        self.logger.info(f"Obtendo informações do adaptador: {adapter_name}")
        
        try:
            adapters = self.detect_adapters()
            
            for adapter in adapters:
                if adapter['name'] == adapter_name:
                    # Adicionar informações de energia
                    power_status = self.check_power_status(adapter_name)
                    adapter['power_status'] = power_status['adapters'].get(adapter_name, {})
                    
                    self.logger.info(f"Informações obtidas para: {adapter_name}")
                    return adapter
            
            raise ValueError(f"Adaptador '{adapter_name}' não encontrado")
            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do adaptador {adapter_name}: {e}")
            raise
    
    def list_adapters(self) -> List[str]:
        """
        Lista apenas os nomes dos adaptadores disponíveis.
        
        Returns:
            List[str]: Lista de nomes dos adaptadores
        """
        self.logger.info("Listando adaptadores disponíveis")
        
        try:
            adapters = self.detect_adapters()
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
def disable_power_saving_all():
    """Desativa a economia de energia para todos os adaptadores."""
    manager = NetworkAdapterManager()
    return manager.disable_power_saving()


def enable_power_saving_all():
    """Reativa a economia de energia para todos os adaptadores."""
    manager = NetworkAdapterManager()
    return manager.enable_power_saving()


def check_all_adapters_status():
    """Verifica o status de todos os adaptadores."""
    manager = NetworkAdapterManager()
    return manager.check_power_status()


def list_network_adapters():
    """Lista todos os adaptadores de rede disponíveis."""
    manager = NetworkAdapterManager()
    return manager.list_adapters()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação de Adaptadores de Rede ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = NetworkAdapterManager()
        
        # Listar adaptadores disponíveis
        print("1. Adaptadores de Rede Disponíveis:")
        adapters = manager.list_adapters()
        for i, adapter in enumerate(adapters, 1):
            print(f"   {i}. {adapter}")
        print()
        
        # Verificar status atual
        print("2. Status Atual da Economia de Energia:")
        status = manager.check_power_status()
        for adapter_name, adapter_status in status['adapters'].items():
            print(f"   {adapter_name}: {adapter_status['current_status']}")
        print()
        
        # Desativar economia de energia
        print("3. Desativando Economia de Energia...")
        success = manager.disable_power_saving()
        if success:
            print("   ✓ Economia de energia desativada com sucesso!")
        else:
            print("   ✗ Falha ao desativar economia de energia")
        print()
        
        # Verificar novo status
        print("4. Novo Status (após desativação):")
        new_status = manager.check_power_status()
        for adapter_name, adapter_status in new_status['adapters'].items():
            print(f"   {adapter_name}: {adapter_status['current_status']}")
        print()
        
        print("Operação concluída!")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")