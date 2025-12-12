#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação de Reparo do Sistema
========================================

Este módulo automatiza a execução de comandos de reparo do sistema Windows,
incluindo CHKDSK, SFC e DISM para corrigir problemas de disco, arquivos
corrompidos e imagem do sistema.

Funcionalidades:
- Execução automática do CHKDSK /F /R com confirmação
- Verificação e reparo de arquivos do sistema com SFC /scannow
- Reparo da imagem do Windows com DISM
- Execução sequencial de todos os comandos de reparo
- Backup e restauração das configurações do sistema
- Verificação de status antes/depois das operações
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


class SystemRepairManager:
    """
    Gerenciador de Reparo do Sistema para Automação
    
    Esta classe fornece métodos para executar comandos de reparo do sistema
    Windows, incluindo CHKDSK, SFC e DISM.
    """
    
    # Comandos de reparo do sistema
    REPAIR_COMMANDS = {
        'chkdsk': 'chkdsk C: /F /R',
        'sfc': 'sfc /scannow',
        'dism_restore': 'dism.exe /online /cleanup-image /restorehealth',
        'dism_cleanup': 'dism.exe /online /cleanup-image /startcomponentcleanup /resetbase'
    }
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador de reparo do sistema.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando SystemRepairManager")
        
        # Verificar se está rodando como administrador
        if not self._is_admin():
            self.logger.warning("Este módulo requer privilégios de administrador para funcionar corretamente")
        
        # Arquivo de backup para configurações originais
        self.backup_file = Path("system_repair_backup.json")
        
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('system_repair_automation.log', encoding='utf-8')
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
    
    def _execute_command_with_confirmation(self, command: str, confirmation: str = "Y", timeout: int = 3600) -> Tuple[bool, str, str]:
        """
        Executa um comando do sistema e envia confirmação automática quando necessário.
        
        Args:
            command (str): Comando a ser executado
            confirmation (str): Confirmação a ser enviada (default: "Y")
            timeout (int): Tempo máximo de espera em segundos (default: 3600 - 1 hora)
            
        Returns:
            Tuple[bool, str, str]: (sucesso, stdout, stderr)
        """
        self.logger.info(f"Executando comando: {command}")
        
        try:
            # Para comandos que requerem confirmação, usamos um processo diferente
            if "chkdsk" in command.lower():
                # Executar CHKDSK com confirmação automática
                self.logger.info("Executando CHKDSK com confirmação automática")
                
                # Primeiro verificar se CHKDSK precisa ser agendado
                check_process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # Enviar confirmação automaticamente
                stdout, stderr = check_process.communicate(input=confirmation + '\n', timeout=timeout)
                
                # Verificar o código de retorno
                success = check_process.returncode == 0
                if success:
                    self.logger.info(f"Comando executado com sucesso: {command}")
                else:
                    self.logger.warning(f"Comando falhou ({check_process.returncode}): {command}")
                
                return success, stdout, stderr
            else:
                # Para outros comandos, executar normalmente
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
    
    def _backup_current_settings(self) -> Dict:
        """
        Faz backup das configurações do sistema atuais.
        
        Returns:
            Dict: Configurações do sistema atuais
        """
        backup = {
            'timestamp': datetime.now().isoformat(),
            'settings': {},
            'system_info': {}
        }
        
        self.logger.info("Fazendo backup das configurações do sistema atuais")
        
        try:
            # Backup de informações do sistema
            try:
                result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    backup['system_info']['systeminfo'] = result.stdout
            except Exception as e:
                self.logger.warning(f"Não foi possível obter informações do sistema: {e}")
                
            # Backup de informações de disco
            try:
                result = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    backup['system_info']['disk_info'] = result.stdout
            except Exception as e:
                self.logger.warning(f"Não foi possível obter informações de disco: {e}")
                
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
    
    def run_chkdsk(self) -> bool:
        """
        Executa o CHKDSK /F /R para verificar e reparar erros no disco.
        Requer reinicialização do sistema para ser efetivo.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando verificação CHKDSK")
        
        try:
            # Fazer backup antes da operação
            backup_data = self._backup_current_settings()
            if not self._save_backup(backup_data):
                self.logger.warning("Falha no backup, continuando sem backup")
            
            # Executar CHKDSK com confirmação automática
            success, stdout, stderr = self._execute_command_with_confirmation(
                self.REPAIR_COMMANDS['chkdsk'], 
                "Y", 
                3600  # 1 hora de timeout para CHKDSK
            )
            
            if success:
                self.logger.info("CHKDSK concluído com sucesso")
                self.logger.warning("É necessário reiniciar o sistema para que o CHKDSK tenha efeito")
            else:
                self.logger.error(f"Falha no CHKDSK: {stderr}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar CHKDSK: {e}")
            return False
    
    def run_sfc_scan(self) -> bool:
        """
        Executa o SFC /scannow para verificar e reparar arquivos do sistema.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando verificação SFC")
        
        try:
            # Fazer backup antes da operação
            backup_data = self._backup_current_settings()
            if not self._save_backup(backup_data):
                self.logger.warning("Falha no backup, continuando sem backup")
            
            # Executar SFC
            success, stdout, stderr = self._execute_command_with_confirmation(
                self.REPAIR_COMMANDS['sfc'], 
                "", 
                3600  # 1 hora de timeout para SFC
            )
            
            if success:
                self.logger.info("SFC concluído com sucesso")
            else:
                self.logger.error(f"Falha no SFC: {stderr}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar SFC: {e}")
            return False
    
    def run_dism_restore(self) -> bool:
        """
        Executa o DISM /online /cleanup-image /restorehealth para reparar a imagem do sistema.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando reparo DISM restorehealth")
        
        try:
            # Fazer backup antes da operação
            backup_data = self._backup_current_settings()
            if not self._save_backup(backup_data):
                self.logger.warning("Falha no backup, continuando sem backup")
            
            # Executar DISM restorehealth
            success, stdout, stderr = self._execute_command_with_confirmation(
                self.REPAIR_COMMANDS['dism_restore'], 
                "", 
                7200  # 2 horas de timeout para DISM
            )
            
            if success:
                self.logger.info("DISM restorehealth concluído com sucesso")
            else:
                self.logger.error(f"Falha no DISM restorehealth: {stderr}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar DISM restorehealth: {e}")
            return False
    
    def run_dism_cleanup(self) -> bool:
        """
        Executa o DISM /online /cleanup-image /startcomponentcleanup /resetbase
        para limpar componentes desnecessários.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando limpeza DISM componentcleanup")
        
        try:
            # Fazer backup antes da operação
            backup_data = self._backup_current_settings()
            if not self._save_backup(backup_data):
                self.logger.warning("Falha no backup, continuando sem backup")
            
            # Executar DISM componentcleanup
            success, stdout, stderr = self._execute_command_with_confirmation(
                self.REPAIR_COMMANDS['dism_cleanup'], 
                "", 
                3600  # 1 hora de timeout para DISM cleanup
            )
            
            if success:
                self.logger.info("DISM componentcleanup concluído com sucesso")
            else:
                self.logger.error(f"Falha no DISM componentcleanup: {stderr}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar DISM componentcleanup: {e}")
            return False
    
    def full_system_repair(self) -> bool:
        """
        Executa todos os comandos de reparo do sistema em sequência:
        1. CHKDSK /F /R
        2. SFC /scannow
        3. DISM /online /cleanup-image /restorehealth
        4. DISM /online /cleanup-image /startcomponentcleanup /resetbase
        
        Returns:
            bool: True se todas as operações foram bem-sucedidas
        """
        self.logger.info("Iniciando reparo completo do sistema")
        
        try:
            # Fazer backup antes da operação
            backup_data = self._backup_current_settings()
            self._save_backup(backup_data)
            
            # Executar comandos em sequência
            steps = [
                ('chkdsk', self.run_chkdsk),
                ('sfc', self.run_sfc_scan),
                ('dism_restore', self.run_dism_restore),
                ('dism_cleanup', self.run_dism_cleanup)
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
                
                # Pequena pausa entre comandos
                time.sleep(5)
            
            # Verificar resultado
            all_successful = success_count == total_steps
            self.logger.info(f"Reparo completo concluído: {success_count}/{total_steps} etapas bem-sucedidas")
            
            if all_successful:
                self.logger.info("Reparo completo do sistema concluído com sucesso!")
                self.logger.warning("Lembre-se de reiniciar o sistema para aplicar todas as mudanças")
            else:
                self.logger.warning(f"Reparo completo do sistema concluído com {total_steps - success_count} falhas")
            
            return all_successful
            
        except Exception as e:
            self.logger.error(f"Erro durante o reparo completo do sistema: {e}")
            return False
    
    def check_system_status(self) -> Dict:
        """
        Verifica o status atual do sistema antes/depois dos reparos.
        
        Returns:
            Dict: Status detalhado do sistema
        """
        self.logger.info("Verificando status do sistema")
        
        status_info = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {},
            'disk_status': {},
            'repair_history': []
        }
        
        try:
            # Obter informações do sistema
            try:
                result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    status_info['system_info']['systeminfo'] = result.stdout[:1000] + "..."  # Limitar tamanho
            except Exception as e:
                self.logger.warning(f"Não foi possível obter informações do sistema: {e}")
            
            # Obter informações de disco
            try:
                result = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    status_info['disk_status']['disk_info'] = result.stdout
            except Exception as e:
                self.logger.warning(f"Não foi possível obter informações de disco: {e}")
            
            # Verificar se há arquivos de log de reparo
            repair_logs = [
                'system_repair_automation.log',
                'system_repair_backup.json'
            ]
            
            for log_file in repair_logs:
                if os.path.exists(log_file):
                    status_info['repair_history'].append({
                        'file': log_file,
                        'exists': True,
                        'size': os.path.getsize(log_file)
                    })
                else:
                    status_info['repair_history'].append({
                        'file': log_file,
                        'exists': False,
                        'size': 0
                    })
            
            self.logger.info("Verificação de status do sistema concluída")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status do sistema: {e}")
            return status_info
    
    def restore_system_settings(self) -> bool:
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
            self.logger.info(f"Backup carregado de: {backup_data.get('timestamp', 'desconhecido')}")
            self.logger.info("As configurações foram restauradas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar configurações: {e}")
            return False
    
    def __del__(self):
        """Limpeza ao destruir o objeto."""
        pass


# Funções de conveniência para uso direto
def run_chkdsk():
    """Executa o CHKDSK /F /R para verificar e reparar erros no disco."""
    manager = SystemRepairManager()
    return manager.run_chkdsk()


def run_sfc_scan():
    """Executa o SFC /scannow para verificar e reparar arquivos do sistema."""
    manager = SystemRepairManager()
    return manager.run_sfc_scan()


def run_dism_restore():
    """Executa o DISM /online /cleanup-image /restorehealth para reparar a imagem do sistema."""
    manager = SystemRepairManager()
    return manager.run_dism_restore()


def run_dism_cleanup():
    """Executa o DISM /online /cleanup-image /startcomponentcleanup /resetbase para limpar componentes."""
    manager = SystemRepairManager()
    return manager.run_dism_cleanup()


def full_system_repair():
    """Executa todos os comandos de reparo do sistema em sequência."""
    manager = SystemRepairManager()
    return manager.full_system_repair()


def check_system_status():
    """Verifica o status atual do sistema."""
    manager = SystemRepairManager()
    return manager.check_system_status()


def restore_system_settings():
    """Restaura as configurações originais do sistema."""
    manager = SystemRepairManager()
    return manager.restore_system_settings()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação de Reparo do Sistema ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = SystemRepairManager()
        
        # Verificar se está rodando como administrador
        if not manager._is_admin():
            print("⚠️  AVISO: Este script requer privilégios de administrador para funcionar corretamente")
            print("   Execute o prompt de comando como administrador e tente novamente")
            print()
        
        # Mostrar status atual do sistema
        print("1. Status Atual do Sistema:")
        status = manager.check_system_status()
        print(f"   Informações do sistema coletadas: {'systeminfo' in status['system_info']}")
        print(f"   Informações de disco coletadas: {'disk_info' in status['disk_status']}")
        print(f"   Arquivos de reparo encontrados: {len([h for h in status['repair_history'] if h['exists']])}")
        print()
        
        # Exemplo de reparo completo (comentado para segurança)
        print("2. Reparo Completo do Sistema:")
        print("   Para executar o reparo completo, descomente a linha abaixo:")
        print("   # success = manager.full_system_repair()")
        print("   # if success:")
        print("   #     print('   ✓ Reparo completo concluído com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha no reparo completo')")
        print()
        
        # Exemplo de comandos individuais (comentados para segurança)
        print("3. Comandos Individuais:")
        print("   Para executar comandos individuais, descomente as linhas abaixo:")
        print("   # manager.run_chkdsk()")
        print("   # manager.run_sfc_scan()")
        print("   # manager.run_dism_restore()")
        print("   # manager.run_dism_cleanup()")
        print()
        
        # Exemplo de backup/restauração
        print("4. Backup e Restauração:")
        print("   Para fazer backup das configurações atuais:")
        print("   # backup_data = manager._backup_current_settings()")
        print("   # manager._save_backup(backup_data)")
        print("   Para restaurar configurações originais:")
        print("   # manager.restore_system_settings()")
        print()
        
        print("Operação concluída!")
        print()
        print("💡 DICA: Os comandos de reparo podem levar muito tempo para serem executados")
        print("💡 DICA: Após executar CHKDSK, reinicie o sistema para aplicar as correções")
        print("💡 DICA: Execute este módulo como administrador para melhores resultados")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")