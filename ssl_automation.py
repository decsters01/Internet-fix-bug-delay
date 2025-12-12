#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Automação SSL/TLS
===========================

Este módulo automatiza a limpeza do estado SSL/TLS no Windows,
essencial para resolver problemas de handshake e conexão segura com a Blaze.

Funcionalidades:
- Limpeza de cache SSL/TLS
- Limpeza de certificados pessoais
- Limpeza de certificados de autoridade certificadora
- Limpeza completa do estado SSL do sistema
- Verificação de status SSL/TLS
- Execução sequencial de todas as operações

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


class SSLManager:
    """
    Gerenciador de Limpeza SSL/TLS para Automação
    
    Esta classe fornece métodos para limpar certificados SSL/TLS em cache
    e resolver problemas de handshake seguro no Windows.
    
    Funcionalidades:
    - Limpeza de cache SSL/TLS
    - Limpeza de certificados pessoais
    - Limpeza de certificados de autoridade certificadora
    - Limpeza completa do estado SSL do sistema
    - Verificação de status SSL/TLS
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inicializa o gerenciador SSL/TLS.
        
        Args:
            log_level (int): Nível de logging (default: logging.INFO)
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando SSLManager")
        
        # Verificar se está rodando como administrador
        if not self._is_admin():
            self.logger.warning("Este módulo pode requerer privilégios de administrador para funcionar corretamente")
        
        # Comandos certutil para limpeza SSL/TLS
        self.SSL_COMMANDS = {
            'clear_cache': 'certutil -delstore -user "MY" *',
            'clear_personal': 'certutil -delstore -user "MY" *',
            'clear_ca': 'certutil -delstore -user "CA" *',
            'list_personal': 'certutil -store -user "MY"',
            'list_ca': 'certutil -store -user "CA"'
        }
        
        # Comandos alternativos para limpeza mais específica
        self.SSL_ALT_COMMANDS = {
            'clear_ssl_state': 'certutil -delstore "Root" *',
            'clear_all_stores': 'certutil -delstore -user "MY" * && certutil -delstore -user "CA" * && certutil -delstore -user "ROOT" *'
        }
    
    def _setup_logging(self, log_level: int) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('ssl_automation.log', encoding='utf-8')
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
    
    def _get_ssl_status(self) -> Dict:
        """
        Obtém o status atual dos certificados SSL/TLS.
        
        Returns:
            Dict: Status detalhado dos certificados
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'personal_certificates': 0,
            'ca_certificates': 0,
            'personal_cert_list': [],
            'ca_cert_list': []
        }
        
        try:
            # Listar certificados pessoais
            success, stdout, stderr = self._execute_command(self.SSL_COMMANDS['list_personal'], 15)
            if success:
                # Contar certificados (aproximadamente)
                cert_count = stdout.count("Certificate")
                status['personal_certificates'] = cert_count
                
                # Extrair nomes dos certificados
                lines = stdout.split('\n')
                for line in lines:
                    if "CN=" in line:
                        # Extrair Common Name
                        try:
                            cn_start = line.find("CN=")
                            cn_end = line.find(",", cn_start)
                            if cn_end == -1:
                                cn_end = len(line)
                            cn = line[cn_start:cn_end].strip()
                            if cn not in status['personal_cert_list']:
                                status['personal_cert_list'].append(cn)
                        except:
                            pass
            
            # Listar certificados CA
            success, stdout, stderr = self._execute_command(self.SSL_COMMANDS['list_ca'], 15)
            if success:
                # Contar certificados (aproximadamente)
                cert_count = stdout.count("Certificate")
                status['ca_certificates'] = cert_count
                
                # Extrair nomes dos certificados
                lines = stdout.split('\n')
                for line in lines:
                    if "CN=" in line:
                        # Extrair Common Name
                        try:
                            cn_start = line.find("CN=")
                            cn_end = line.find(",", cn_start)
                            if cn_end == -1:
                                cn_end = len(line)
                            cn = line[cn_start:cn_end].strip()
                            if cn not in status['ca_cert_list']:
                                status['ca_cert_list'].append(cn)
                        except:
                            pass
                                
        except Exception as e:
            self.logger.warning(f"Não foi possível obter status SSL: {e}")
        
        return status
    
    def clear_ssl_cache(self) -> bool:
        """
        Limpa o cache SSL/TLS.
        Remove certificados em cache que podem causar problemas de handshake.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando limpeza do cache SSL/TLS")
        
        try:
            # Obter status antes
            status_before = self._get_ssl_status()
            self.logger.info(f"Status antes da limpeza: {status_before['personal_certificates']} certificados pessoais")
            
            # Executar comando de limpeza
            success, stdout, stderr = self._execute_command(self.SSL_COMMANDS['clear_cache'])
            
            if success:
                self.logger.info("Limpeza do cache SSL/TLS concluída com sucesso")
            else:
                self.logger.error(f"Falha na limpeza do cache SSL/TLS: {stderr}")
            
            # Obter status depois
            status_after = self._get_ssl_status()
            self.logger.info(f"Status após a limpeza: {status_after['personal_certificates']} certificados pessoais")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao executar limpeza do cache SSL/TLS: {e}")
            return False
    
    def clear_personal_certificates(self) -> bool:
        """
        Limpa os certificados pessoais do usuário.
        Remove todos os certificados da loja pessoal do usuário.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando limpeza dos certificados pessoais")
        
        try:
            # Obter status antes
            status_before = self._get_ssl_status()
            self.logger.info(f"Status antes da limpeza: {status_before['personal_certificates']} certificados pessoais")
            
            # Executar comando de limpeza
            success, stdout, stderr = self._execute_command(self.SSL_COMMANDS['clear_personal'])
            
            if success:
                self.logger.info("Limpeza dos certificados pessoais concluída com sucesso")
            else:
                self.logger.error(f"Falha na limpeza dos certificados pessoais: {stderr}")
            
            # Obter status depois
            status_after = self._get_ssl_status()
            self.logger.info(f"Status após a limpeza: {status_after['personal_certificates']} certificados pessoais")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar certificados pessoais: {e}")
            return False
    
    def clear_ca_certificates(self) -> bool:
        """
        Limpa os certificados de autoridade certificadora.
        Remove todos os certificados da loja de autoridades certificadoras.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando limpeza dos certificados de autoridade certificadora")
        
        try:
            # Obter status antes
            status_before = self._get_ssl_status()
            self.logger.info(f"Status antes da limpeza: {status_before['ca_certificates']} certificados CA")
            
            # Executar comando de limpeza
            success, stdout, stderr = self._execute_command(self.SSL_COMMANDS['clear_ca'])
            
            if success:
                self.logger.info("Limpeza dos certificados CA concluída com sucesso")
            else:
                self.logger.error(f"Falha na limpeza dos certificados CA: {stderr}")
            
            # Obter status depois
            status_after = self._get_ssl_status()
            self.logger.info(f"Status após a limpeza: {status_after['ca_certificates']} certificados CA")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar certificados CA: {e}")
            return False
    
    def full_ssl_cleanup(self) -> bool:
        """
        Executa a limpeza completa SSL/TLS.
        Executa todas as operações de limpeza em sequência:
        1. Limpeza de certificados pessoais
        2. Limpeza de certificados CA
        3. Limpeza de cache SSL/TLS
        
        Returns:
            bool: True se todas as operações foram bem-sucedidas
        """
        self.logger.info("Iniciando limpeza completa SSL/TLS")
        
        try:
            # Obter status antes
            status_before = self._get_ssl_status()
            self.logger.info(f"Status inicial: {status_before['personal_certificates']} pessoais, {status_before['ca_certificates']} CA")
            
            # Executar comandos em sequência
            steps = [
                ('personal', self.clear_personal_certificates),
                ('ca', self.clear_ca_certificates),
                ('cache', self.clear_ssl_cache)
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
            status_after = self._get_ssl_status()
            self.logger.info(f"Status final: {status_after['personal_certificates']} pessoais, {status_after['ca_certificates']} CA")
            
            # Verificar resultado
            all_successful = success_count == total_steps
            self.logger.info(f"Limpeza completa concluída: {success_count}/{total_steps} etapas bem-sucedidas")
            
            if all_successful:
                self.logger.info("Limpeza completa SSL/TLS concluída com sucesso!")
            else:
                self.logger.warning(f"Limpeza completa SSL/TLS concluída com {total_steps - success_count} falhas")
            
            return all_successful
            
        except Exception as e:
            self.logger.error(f"Erro durante a limpeza completa SSL/TLS: {e}")
            return False
    
    def clear_ssl_state(self) -> bool:
        """
        Limpa o estado completo SSL do sistema.
        Remove todos os certificados e estados SSL em cache.
        
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        self.logger.info("Iniciando limpeza completa do estado SSL")
        
        try:
            # Obter status antes
            status_before = self._get_ssl_status()
            self.logger.info(f"Status antes da limpeza: {status_before['personal_certificates']} pessoais, {status_before['ca_certificates']} CA")
            
            # Executar comando de limpeza completa
            success, stdout, stderr = self._execute_command(self.SSL_ALT_COMMANDS['clear_all_stores'])
            
            if success:
                self.logger.info("Limpeza completa do estado SSL concluída com sucesso")
            else:
                self.logger.error(f"Falha na limpeza completa do estado SSL: {stderr}")
            
            # Obter status depois
            status_after = self._get_ssl_status()
            self.logger.info(f"Status após a limpeza: {status_after['personal_certificates']} pessoais, {status_after['ca_certificates']} CA")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar estado SSL completo: {e}")
            return False
    
    def check_ssl_status(self) -> Dict:
        """
        Verifica o status atual dos certificados SSL/TLS.
        
        Returns:
            Dict: Status detalhado dos certificados
        """
        self.logger.info("Verificando status SSL/TLS")
        return self._get_ssl_status()


# Funções de conveniência para uso direto
def clear_ssl_cache():
    """Limpa o cache SSL/TLS."""
    manager = SSLManager()
    return manager.clear_ssl_cache()


def clear_personal_certificates():
    """Limpa os certificados pessoais do usuário."""
    manager = SSLManager()
    return manager.clear_personal_certificates()


def clear_ca_certificates():
    """Limpa os certificados de autoridade certificadora."""
    manager = SSLManager()
    return manager.clear_ca_certificates()


def full_ssl_cleanup():
    """Executa a limpeza completa SSL/TLS."""
    manager = SSLManager()
    return manager.full_ssl_cleanup()


def check_ssl_status():
    """Verifica o status atual dos certificados SSL/TLS."""
    manager = SSLManager()
    return manager.check_ssl_status()


def clear_ssl_state():
    """Limpa o estado completo SSL do sistema."""
    manager = SSLManager()
    return manager.clear_ssl_state()


# Exemplo de uso
if __name__ == "__main__":
    print("=== Módulo de Automação SSL/TLS ===")
    print()
    
    try:
        # Criar instância do gerenciador
        manager = SSLManager()
        
        # Verificar se está rodando como administrador
        if not manager._is_admin():
            print("⚠️  AVISO: Este script pode requerer privilégios de administrador para funcionar corretamente")
            print("   Execute o prompt de comando como administrador e tente novamente")
            print()
        
        # Verificar status atual
        print("1. Status Atual dos Certificados SSL/TLS:")
        status = manager.check_ssl_status()
        print(f"   Certificados pessoais: {status['personal_certificates']}")
        print(f"   Certificados CA: {status['ca_certificates']}")
        print()
        
        # Executar limpeza completa (comentado para segurança)
        print("2. Limpeza Completa SSL/TLS:")
        print("   Para executar a limpeza completa, descomente a linha abaixo:")
        print("   # success = manager.full_ssl_cleanup()")
        print("   # if success:")
        print("   #     print('   ✓ Limpeza completa concluída com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha na limpeza completa')")
        print()
        
        # Executar limpeza de estado SSL (comentado para segurança)
        print("3. Limpeza de Estado SSL Completo:")
        print("   Para executar a limpeza de estado SSL completo, descomente a linha abaixo:")
        print("   # success = manager.clear_ssl_state()")
        print("   # if success:")
        print("   #     print('   ✓ Limpeza de estado SSL concluída com sucesso!')")
        print("   # else:")
        print("   #     print('   ✗ Falha na limpeza de estado SSL')")
        print()
        
        # Exemplo de comandos individuais (comentados para segurança)
        print("4. Comandos Individuais:")
        print("   Para executar comandos individuais, descomente as linhas abaixo:")
        print("   # manager.clear_ssl_cache()")
        print("   # manager.clear_ca_certificates()")
        print("   # manager.clear_ssl_state()")
        print()
        
        print("Operação concluída!")
        print()
        print("💡 DICA: Após executar a limpeza, reinicie o navegador e o aplicativo da Blaze")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        logging.error(f"Erro na execução principal: {e}")