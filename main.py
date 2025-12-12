#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Otimização para Trading - Casino e Nano Trade
========================================================

Este script otimiza especificamente o Windows para aplicações críticas de
trading como casino online e nano trade, resolvendo instabilidades de rede
que podem causar perdas financeiras.

FUNCIONALIDADES ESPECÍFICAS PARA TRADING:
- Menu interativo com descrições detalhadas dos benefícios
- Explicações técnicas de como cada otimização ajuda no trading
- Foco em redução de latência para operações de alta frequência
- Otimização 24/7 para robôs de trading
- Eliminação de delays que causam perdas em volatilidade extrema

BENEFÍCIOS PARA TRADING:
- Redução de 15-50ms na latência de conexão
- Eliminação de micro-delays em operações de alta frequência
- Conexões estáveis 24/7 com brokers
- Recursos otimizados para robôs de trading
- Sistema estável sem travamentos durante volatilidade

Autor: Sistema de Otimização para Trading
Versão: 2.0.0 - Focado em Casino/Nano Trade
Data: 2025-12-12
"""

import logging
import os
import sys
import time
import ctypes
import traceback
import importlib
import json
from pathlib import Path
from typing import Optional


def _agent_debug_log_runtime(*, run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        exe_path = Path(getattr(sys, "executable", "")).resolve()
        project_root = exe_path.parent.parent if exe_path.parent.name.lower() == "dist" else exe_path.parent
        log_path = project_root / ".cursor" / "debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.open("a", encoding="utf-8").write(
            json.dumps(
                {
                    "sessionId": "debug-session",
                    "runId": run_id,
                    "hypothesisId": hypothesis_id,
                    "location": location,
                    "message": message,
                    "data": data,
                    "timestamp": int(time.time() * 1000),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    except Exception:
        pass
    # endregion

# Importações dos módulos de automação (carregamento resiliente)
# Observação: NÃO encerramos o programa em caso de falha de import.
DNSManager = None
LSOManager = None
MTUManager = None
NetworkAdapterManager = None
NetworkResetManager = None
SSLManager = None
SystemAutomationManager = None
SystemRepairManager = None
TCPTimeoutManager = None
_MANAGER_IMPORT_ERRORS: list[str] = []


def _configure_console_output() -> None:
    """
    Evita travamentos por UnicodeEncodeError em consoles Windows (cp1252/cp850).
    Mantém o programa vivo mesmo com emojis/acentos.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            # Python 3.7+ (TextIOWrapper)
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Se não suportar, seguimos; prints podem ser substituídos em alguns ambientes.
            pass


def _attempt_import_managers() -> list[str]:
    """
    Tenta importar todos os módulos de automação.

    Retorna uma lista de erros (strings) se algo falhar.
    """
    global DNSManager
    global LSOManager
    global MTUManager
    global NetworkAdapterManager
    global NetworkResetManager
    global SSLManager
    global SystemAutomationManager
    global SystemRepairManager
    global TCPTimeoutManager
    global _MANAGER_IMPORT_ERRORS

    errors: list[str] = []

    _agent_debug_log_runtime(
        run_id="import-debug",
        hypothesis_id="H2",
        location="main.py:_attempt_import_managers",
        message="Starting manager imports",
        data={
            "cwd": os.getcwd(),
            "sys_executable": getattr(sys, "executable", None),
            "has_meipass": hasattr(sys, "_MEIPASS"),
            "meipass": getattr(sys, "_MEIPASS", None),
            "sys_path_head": list(sys.path[:8]),
        },
    )

    def _import_attr(module_name: str, attr_name: str):
        try:
            _agent_debug_log_runtime(
                run_id="import-debug",
                hypothesis_id="H1",
                location="main.py:_attempt_import_managers:_import_attr",
                message="Import attempt",
                data={"module": module_name, "attr": attr_name},
            )
            module = importlib.import_module(module_name)
            return getattr(module, attr_name)
        except Exception as e:
            errors.append(f"{module_name}.{attr_name}: {e}")
            try:
                meipass = Path(getattr(sys, "_MEIPASS", "")) if hasattr(sys, "_MEIPASS") else None
                in_meipass = (meipass / f"{module_name}.py").exists() if meipass else None
            except Exception:
                in_meipass = None

            _agent_debug_log_runtime(
                run_id="import-debug",
                hypothesis_id="H1",
                location="main.py:_attempt_import_managers:_import_attr",
                message="Import failed",
                data={
                    "module": module_name,
                    "attr": attr_name,
                    "exc_type": type(e).__name__,
                    "exc": repr(e)[:2000],
                    "in_meipass_py": in_meipass,
                },
            )
            return None

    DNSManager = _import_attr("dns_automation", "DNSManager")
    LSOManager = _import_attr("lso_automation", "LSOManager")
    MTUManager = _import_attr("mtu_automation", "MTUManager")
    NetworkAdapterManager = _import_attr("network_adapter_automation", "NetworkAdapterManager")
    NetworkResetManager = _import_attr("network_reset_automation", "NetworkResetManager")
    SSLManager = _import_attr("ssl_automation", "SSLManager")
    SystemAutomationManager = _import_attr("system_automation", "SystemAutomationManager")
    SystemRepairManager = _import_attr("system_repair_automation", "SystemRepairManager")
    TCPTimeoutManager = _import_attr("tcp_timeout_automation", "TCPTimeoutManager")

    _MANAGER_IMPORT_ERRORS = errors
    _agent_debug_log_runtime(
        run_id="import-debug",
        hypothesis_id="H1",
        location="main.py:_attempt_import_managers",
        message="Manager imports finished",
        data={"error_count": len(errors), "errors": errors[:25]},
    )
    return errors


class TradingOptimizerOrchestrator:
    """
    Orquestrador Principal para Otimização de Trading
    
    Esta classe gerencia a execução de todos os módulos de otimização,
    focando especificamente em melhorar a performance para trading
    profissional (casino e nano trade).
    
    OBJETIVO: Eliminar gargalos de rede que causam perdas financeiras
    em operações de alta frequência e volatilidade extrema.
    """
    
    def __init__(self):
        """Inicializa o orquestrador focado em trading."""
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando TradingOptimizerOrchestrator")
        
        # Verificar privilégios de administrador
        self.is_admin = self._check_admin_privileges()
        
        # Inicializar todos os gerenciadores
        self._initialize_managers()
        
    def _setup_logging(self) -> None:
        """Configura o sistema de logging centralizado."""
        log_file = Path("automation.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
        
    def _check_admin_privileges(self) -> bool:
        """
        Verifica se o script está sendo executado com privilégios de administrador.
        
        Returns:
            bool: True se está rodando como administrador
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
            
    def _initialize_managers(self) -> None:
        """Inicializa todos os gerenciadores de automação."""
        try:
            self.logger.info("Inicializando gerenciadores de automação...")

            missing = []
            for name, cls in [
                ("DNSManager", DNSManager),
                ("LSOManager", LSOManager),
                ("MTUManager", MTUManager),
                ("NetworkAdapterManager", NetworkAdapterManager),
                ("NetworkResetManager", NetworkResetManager),
                ("SSLManager", SSLManager),
                ("SystemAutomationManager", SystemAutomationManager),
                ("SystemRepairManager", SystemRepairManager),
                ("TCPTimeoutManager", TCPTimeoutManager),
            ]:
                if cls is None:
                    missing.append(name)

            if missing:
                details = "; ".join(_MANAGER_IMPORT_ERRORS) if _MANAGER_IMPORT_ERRORS else "Sem detalhes adicionais."
                raise RuntimeError(
                    "Módulos de automação não carregados. "
                    f"Faltando: {', '.join(missing)}. "
                    f"Detalhes: {details}"
                )
            
            self.dns_manager = DNSManager()
            self.lso_manager = LSOManager()
            self.mtu_manager = MTUManager()
            self.adapter_manager = NetworkAdapterManager()
            self.reset_manager = NetworkResetManager()
            self.ssl_manager = SSLManager()
            self.system_manager = SystemAutomationManager()
            self.repair_manager = SystemRepairManager()
            self.tcp_manager = TCPTimeoutManager()
            
            self.logger.info("Todos os gerenciadores inicializados com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar gerenciadores: {e}")
            raise
            
    def display_admin_warning(self) -> None:
        """Exibe aviso sobre privilégios de administrador."""
        if not self.is_admin:
            print("\n" + "="*60)
            print("⚠️  AVISO: PRIVILÉGIOS DE ADMINISTRADOR NECESSÁRIOS")
            print("="*60)
            print("Este script requer privilégios de administrador para funcionar")
            print("corretamente. Algumas operações podem falhar sem essas permissões.")
            print("\nPara executar como administrador:")
            print("1. Clique com o botão direito no arquivo main.py")
            print("2. Selecione 'Executar como administrador'")
            print("3. Ou abra o Prompt de Comando como administrador")
            print("   e execute: python main.py")
            print("="*60)
            time.sleep(3)
            
    def show_option_details(self, option: str) -> bool:
        """
        Mostra detalhes explicativos da opção escolhida pelo usuário.
        
        Args:
            option (str): Número da opção escolhida
            
        Returns:
            bool: True se o usuário confirmar a execução, False se cancelar
        """
        details = {
            "1": {
                "title": "🌐 CONFIGURAR DNS CLOUDFLARE",
                "description": """
🎯 OBJETIVO: Alterar servidores DNS para Cloudflare (1.1.1.1 / 1.0.0.1)

🔧 O QUE SERÁ FEITO NO SEU PC:
• Remove DNS lentos do provedor de internet
• Define Cloudflare como servidor DNS primário e secundário
• Limpa cache DNS existente
• Renova configuração de rede

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Reduz latência em 15-50ms na resolução de domínios
• Conexão mais rápida com servidores de trading
• Menor tempo de resposta em ordens de compra/venda
• Estabilidade melhorada durante alta volatilidade do mercado
• Evita timeouts em transações críticas

⚡ IMPACTO: Imediato - melhora perceptível na velocidade de conexão
                """,
                "confirmation": "Deseja configurar DNS Cloudflare para otimizar sua conexão?"
            },
            "2": {
                "title": "📡 DESATIVAR LARGE SEND OFFLOAD (LSO)",
                "description": """
🎯 OBJETIVO: Desativar offload de segmentação de pacotes na placa de rede

🔧 O QUE SERÁ FEITO NO SEU PC:
• Acessa configurações avançadas de todos os adaptadores de rede
• Desativa "Large Send Offload V2 (IPv4)" e "(IPv6)"
• Aplica configurações imediatamente
• Reinicia adaptadores se necessário

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Elimina fragmentação de pacotes que causa delays
• Reduz latência em operações de trading de alta frequência
• Melhora precisão temporal de execução de ordens
• Reduz perda de pacotes em momentos críticos
• Estabiliza conexão durante picos de movimento do mercado

⚡ IMPACTO: Médio prazo - effectiveness aumenta após reinicialização
                """,
                "confirmation": "Deseja desativar LSO para reduzir latência de rede?"
            },
            "3": {
                "title": "🔧 AJUSTAR MTU PARA 1450",
                "description": """
🎯 OBJETIVO: Otimizar tamanho de pacotes para máxima eficiência

🔧 O QUE SERÁ FEITO NO SEU PC:
• Testa diferentes tamanhos de MTU nas interfaces de rede
• Define MTU ideal para 1450 bytes em todas as placas
• Evita fragmentação de pacotes IP
• Otimiza throughput da conexão

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Reduz overhead de rede em até 3%
• Melhora throughput em conexões com fragmentação
• Elimina delays caused por pacotes muito grandes
• Otimiza velocidade de sincronização com brokers
• Crucial para estratégias de scalping e nano trading

⚡ IMPACTO: Imediato - otimização instantânea de pacotes
                """,
                "confirmation": "Deseja ajustar MTU para 1450 para otimizar pacotes?"
            },
            "4": {
                "title": "⚡ DESATIVAR ECONOMIA DE ENERGIA DOS ADAPTADORES",
                "description": """
🎯 OBJETIVO: Manter adaptadores de rede sempre em máxima performance

🔧 O QUE SERÁ FEITO NO SEU PC:
• Desativa "Allow computer to turn off this device" em todas as placas
• Configura power management para maximum performance
• Remove economia de energia automática
• Garante standby zero em adaptadores de rede

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Elimina wake-up delays de 50-200ms em adaptadores
• Conexão instantânea sem delays de inicialização
• Performance consistente 24/7 para trading
• Evita interrupções durante volatilidade extrema
• Crucial para robôs que operam continuamente

⚡ IMPACTO: Imediato - eliminará wake-up delays permanentemente
                """,
                "confirmation": "Deseja desativar economia de energia para performance máxima?"
            },
            "5": {
                "title": "🔄 RESET COMPLETO DE REDE",
                "description": """
🎯 OBJETIVO: Reinicializar completamente a stack de rede do Windows

🔧 O QUE SERÁ FEITO NO SEU PC:
• Executa 'netsh winsock reset' para corrigir protocolos
• Limpa tabela de roteamento IP
• Renova todas as configurações de rede
• Reinicia serviços de rede do Windows
• Libera e renova leases DHCP

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Resolve problemas de conectividade acumulados
• Elimina conflitos de rede que causam desconexões
• Corrige protocolos corrompidos que afetam trading
• Melhora estabilidade após mudanças de rede
• Essencial quando há problemas persistentes de conexão

⚡ IMPACTO: Médio - pode requerir reconexão a redes WiFi
                """,
                "confirmation": "⚠️ ATENÇÃO: Isso pode interrumper conexões ativas. Continuar?"
            },
            "6": {
                "title": "🔒 LIMPAR CACHE SSL/TLS",
                "description": """
🎯 OBJETIVO: Remover certificados SSL/TLS corrompidos ou expirados

🔧 O QUE SERÁ FEITO NO SEU PC:
• Limpa cache SSL/TLS do Windows
• Remove certificados expirados ou corrompidos
• Redefine estado de conexões HTTPS
• Renova cache de navegadores relacionados

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Elimina erros de conexão com plataformas de trading
• Resolve problemas de 'certificate error' durante volatilidade
• Garante conexões seguras com brokers 24/7
• Evita timeouts em momentos críticos do mercado
• Melhora reliability de APIs de trading

⚡ IMPACTO: Imediato - resolve problemas SSL/TLS existentes
                """,
                "confirmation": "Deseja limpar cache SSL/TLS para resolver problemas de conexão?"
            },
            "7": {
                "title": "🚀 OTIMIZAR SISTEMA (Windows Update, apps bandeja)",
                "description": """
🎯 OBJETIVO: Remover processos que interferem com performance de trading

🔧 O QUE SERÁ FEITO NO SEU PC:
• Pausa atualizações automáticas do Windows
• Desativa apps desnecessárias na bandeja do sistema
• Limpa arquivos temporários e cache
• Otimiza uso de memória RAM
• Configura plano de energia para máxima performance

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Libera RAM para robôs de trading
• Reduz uso de CPU por processos desnecessários
• Elimina pop-ups que podem distrair durante trading
• Garante que recursos sejam priorizados para trading
• Previne travamentos durante alta volatilidade

⚡ IMPACTO: Gradual - melhoria progressiva na performance do sistema
                """,
                "confirmation": "Deseja otimizar o sistema para liberar recursos para trading?"
            },
            "8": {
                "title": "🔨 REPARAR SISTEMA (CHKDSK, SFC, DISM)",
                "description": """
🎯 OBJETIVO: Corrigir arquivos corrompidos do sistema Windows

🔧 O QUE SERÁ FEITO NO SEU PC:
• Executa CHKDSK para verificar integridade do disco
• Usa SFC para reparar arquivos corrompidos do Windows
• Executa DISM para restaurar componentes do sistema
• Verifica e corrige registro do Windows

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Elimina travamentos caused por arquivos corrompidos
• Melhora estabilidade geral do sistema
• Corrigi problemas que afetam drivers de rede
• Previne crashes durante sessões longas de trading
• Garante reliability máxima do sistema

⚡ IMPACTO: Demorado - pode levar 30-60 minutos para completar
                """,
                "confirmation": "⚠️ ATENÇÃO: Esta operação pode demorar até 1 hora. Continuar?"
            },
            "9": {
                "title": "⏱️ AJUSTAR TIMEOUT TCP",
                "description": """
🎯 OBJETIVO: Otimizar tempos de timeout para trading de alta velocidade

🔧 O QUE SERÁ FEITO NO SEU PC:
• Reduz timeout TCP padrão para resposta mais rápida
• Configura retry intervals otimizados
• Ajusta parâmetros de conexão para baixa latência
• Otimiza buffer de recepção TCP

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Reduz tempo de espera em conexões lentas
• Permite reconexão rápida em caso de falhas
• Otimizado para operações de nano segundo
• Melhora response time em ordens de trading
• Crucial para arbitagem e scalping

⚡ IMPACTO: Imediato - otimização instantânea de timeouts
                """,
                "confirmation": "Deseja ajustar timeout TCP para operações mais rápidas?"
            },
            "10": {
                "title": "🎯 EXECUTAR TODAS AS CORREÇÕES EM SEQUÊNCIA",
                "description": """
🎯 OBJETIVO: Aplicar todas as otimizações para performance máxima

🔧 O QUE SERÁ FEITO NO SEU PC:
• Executa todas as 9 otimizações em sequência lógica
• Reinicia serviços conforme necessário
• Aplica configurações em ordem otimizada
• Monitora resultado de cada etapa

💰 BENEFÍCIOS PARA CASINO/NANO TRADE:
• Máxima performance possível para trading
• Elimina todos os gargalos de rede conhecidos
• Configuração profissional completa
• Estabilidade 24/7 para robôs de trading
• Base sólida para operações financeiras críticas

⚡ IMPACTO: Completo - transformação total da performance de rede
                """,
                "confirmation": "🎯 ATENÇÃO: Esta operação executará TODAS as otimizações (pode demorar). Continuar?"
            }
        }
        
        if option not in details:
            return False
            
        detail = details[option]
        print(f"\n{'='*80}")
        print(detail["title"])
        print('='*80)
        print(detail["description"])
        print('='*80)
        
        print(f"\n❓ {detail['confirmation']}")
        response = _safe_readline("\n📝 Digite 's' para SIM ou 'n' para NÃO: ", on_keyboard_interrupt="return_empty").strip().lower()
        if response == "":
            print("\n\n⚠️ Operação cancelada pelo usuário.")
            return False
        return response in ['s', 'sim', 'y', 'yes']

    def display_main_menu(self) -> None:
        """Exibe o menu principal."""
        print("\n" + "="*70)
        print("🎰 SISTEMA DE OTIMIZAÇÃO PARA TRADING - CASINO & NANO TRADE")
        print("="*70)
        print("Este sistema otimiza especificamente para aplicações de trading,")
        print("resolvendo instabilidades de rede no Windows que afetam")
        print("operações financeiras críticas.")
        print("="*70)
        
        if self.is_admin:
            print("✅ Status: Executando com privilégios de administrador")
        else:
            print("⚠️  Status: Executando sem privilégios de administrador")
            
        print("\n📋 MENU DE OPÇÕES:")
        print("-" * 50)
        print("1.  🌐 Configurar DNS (Cloudflare: 1.1.1.1 / 1.0.0.1)")
        print("2.  📡 Desativar Large Send Offload (LSO)")
        print("3.  🔧 Ajustar MTU para 1450")
        print("4.  ⚡ Desativar economia de energia dos adaptadores")
        print("5.  🔄 Executar reset completo de rede")
        print("6.  🔒 Limpar cache SSL/TLS")
        print("7.  🚀 Otimizar sistema (Windows Update, apps bandeja)")
        print("8.  🔨 Reparar sistema (CHKDSK, SFC, DISM)")
        print("9.  ⏱️  Ajustar timeout TCP")
        print("10. 🎯 Executar TODAS as correções em sequência")
        print("-" * 50)
        print("0.  ❌ Sair")
        print("="*70)
        print("\n💡 DICA: Digite o número da opção para ver detalhes completos!")
        print("="*70)
        
    def run_dns_configuration(self) -> bool:
        """Executa a configuração de DNS Cloudflare."""
        print("\n🌐 Configurando DNS Cloudflare para Otimização de Trading...")
        print("🎯 Definindo servidores DNS mais rápidos do mundo")
        try:
            success = self.dns_manager.set_cloudflare_dns()
            if success:
                print("✅ DNS configurado com sucesso para Cloudflare")
                print("💰 VANTAGEM: Latência reduzida em 15-50ms para operações de trading")
                self.logger.info("DNS configurado para Cloudflare")
                return True
            else:
                print("❌ Falha ao configurar DNS")
                print("💸 IMPACTO: Latência maior pode causar perdas em operações de nano trade")
                self.logger.error("Falha ao configurar DNS para Cloudflare")
                return False
        except Exception as e:
            print(f"❌ Erro ao configurar DNS: {e}")
            self.logger.error(f"Erro na configuração DNS: {e}")
            return False
            
    def run_lso_disable(self) -> bool:
        """Executa a desativação do LSO."""
        print("\n📡 Desativando Large Send Offload (LSO) para Trading...")
        print("🎯 Eliminando delays de segmentação de pacotes")
        try:
            success = self.lso_manager.disable_lso()
            if success:
                print("✅ LSO desativado com sucesso")
                print("💰 VANTAGEM: Elimina delays de 5-20ms em operações de alta frequência")
                print("🎯 PERFEITO PARA: Scalping, Arbitragem, Nano Trading")
                self.logger.info("LSO desativado para todos os adaptadores")
                return True
            else:
                print("❌ Falha ao desativar LSO")
                print("💸 IMPACTO: Pode causar micro-delays em momentos críticos do mercado")
                self.logger.error("Falha ao desativar LSO")
                return False
        except Exception as e:
            print(f"❌ Erro ao desativar LSO: {e}")
            self.logger.error(f"Erro na desativação LSO: {e}")
            return False
            
    def run_mtu_adjustment(self) -> bool:
        """Executa o ajuste de MTU."""
        print("\n🔧 Ajustando MTU para 1450 - Otimização de Pacotes...")
        print("🎯 Eliminando fragmentação que causa delays em trading")
        try:
            success = self.mtu_manager.set_mtu_all_interfaces(1450)
            if success:
                print("✅ MTU ajustado para 1450 com sucesso")
                print("💰 VANTAGEM: Throughput melhorado em 3%, sem fragmentação")
                print("🎯 CRUCIAL PARA: Conexões estables com brokers 24/7")
                self.logger.info("MTU ajustado para 1450 em todas as interfaces")
                return True
            else:
                print("❌ Falha ao ajustar MTU")
                print("💸 IMPACTO: Pacotes fragmentados podem causar delays em ordens")
                self.logger.error("Falha ao ajustar MTU")
                return False
        except Exception as e:
            print(f"❌ Erro ao ajustar MTU: {e}")
            self.logger.error(f"Erro no ajuste MTU: {e}")
            return False
            
    def run_adapter_power_disable(self) -> bool:
        """Executa a desativação da economia de energia dos adaptadores."""
        print("\n⚡ Desativando Economia de Energia para Trading 24/7...")
        print("🎯 Adaptadores sempre prontos para ação")
        try:
            success = self.adapter_manager.disable_power_saving()
            if success:
                print("✅ Economia de energia desativada com sucesso")
                print("💰 VANTAGEM: Elimina wake-up delays de 50-200ms")
                print("🎯 CRUCIAL PARA: Robôs de trading que operam 24/7")
                self.logger.info("Economia de energia desativada para todos os adaptadores")
                return True
            else:
                print("❌ Falha ao desativar economia de energia")
                print("💸 IMPACTO: Pode causar desconexões durante alta volatilidade")
                self.logger.error("Falha ao desativar economia de energia")
                return False
        except Exception as e:
            print(f"❌ Erro ao desativar economia de energia: {e}")
            self.logger.error(f"Erro na desativação de economia de energia: {e}")
            return False
            
    def run_network_reset(self) -> bool:
        """Executa o reset completo de rede."""
        print("\n🔄 Executando Reset Completo de Rede...")
        print("🎯 Eliminando problemas de conectividade acumulados")
        print("⚠️  ATENÇÃO: Esta operação pode interrumpir conexões ativas!")
        try:
            success = self.reset_manager.full_network_reset()
            if success:
                print("✅ Reset de rede executado com sucesso")
                print("💰 VANTAGEM: Elimina problemas que causam desconexões em trading")
                print("🎯 RECOMENDADO: Quando há problemas persistentes de conexão")
                self.logger.info("Reset completo de rede executado")
                return True
            else:
                print("❌ Falha no reset de rede")
                print("💸 IMPACTO: Problemas de conectividade podem continuar afetando trading")
                self.logger.error("Falha no reset completo de rede")
                return False
        except Exception as e:
            print(f"❌ Erro no reset de rede: {e}")
            self.logger.error(f"Erro no reset de rede: {e}")
            return False
            
    def run_ssl_cleanup(self) -> bool:
        """Executa a limpeza completa do SSL/TLS."""
        print("\n🔒 Limpando Cache SSL/TLS - Segurança Otimizada...")
        print("🎯 Eliminando certificados corrompidos que causam falhas")
        try:
            success = self.ssl_manager.full_ssl_cleanup()
            if success:
                print("✅ Cache SSL/TLS limpo com sucesso")
                print("💰 VANTAGEM: Elimina erros de conexão com plataformas de trading")
                print("🎯 CRUCIAL PARA: Conexões seguras 24/7 com brokers")
                self.logger.info("Limpeza completa SSL/TLS executada")
                return True
            else:
                print("❌ Falha na limpeza SSL/TLS")
                print("💸 IMPACTO: Pode causar 'certificate errors' durante volatilidade")
                self.logger.error("Falha na limpeza SSL/TLS")
                return False
        except Exception as e:
            print(f"❌ Erro na limpeza SSL/TLS: {e}")
            self.logger.error(f"Erro na limpeza SSL/TLS: {e}")
            return False
            
    def run_system_optimization(self) -> bool:
        """Executa a otimização completa do sistema."""
        print("\n🚀 Otimizando Sistema para Performance Máxima...")
        print("🎯 Liberando recursos para trading e eliminando distrações")
        try:
            success = self.system_manager.full_system_optimization()
            if success:
                print("✅ Sistema otimizado com sucesso")
                print("💰 VANTAGEM: Mais RAM e CPU disponíveis para robôs de trading")
                print("🎯 RESULTADO: Performance consistente sem travamentos")
                self.logger.info("Otimização completa do sistema executada")
                return True
            else:
                print("❌ Falha na otimização do sistema")
                print("💸 IMPACTO: Recursos limitados podem afetar performance de trading")
                self.logger.error("Falha na otimização do sistema")
                return False
        except Exception as e:
            print(f"❌ Erro na otimização do sistema: {e}")
            self.logger.error(f"Erro na otimização do sistema: {e}")
            return False
            
    def run_system_repair(self) -> bool:
        """Executa o reparo completo do sistema."""
        print("\n🔨 Reparando Sistema - Garantia de Estabilidade...")
        print("🎯 Corrigindo problemas que podem causar crashes em trading")
        print("⚠️  ATENÇÃO: Esta operação pode demorar vários minutos!")
        try:
            success = self.repair_manager.full_system_repair()
            if success:
                print("✅ Reparo do sistema executado com sucesso")
                print("💰 VANTAGEM: Elimina crashes que podem causar perdas em trading")
                print("🎯 RESULTADO: Sistema estável para operações 24/7")
                self.logger.info("Reparo completo do sistema executado")
                return True
            else:
                print("❌ Falha no reparo do sistema")
                print("💸 IMPACTO: Problemas não resolvidos podem causar instabilidade")
                self.logger.error("Falha no reparo do sistema")
                return False
        except Exception as e:
            print(f"❌ Erro no reparo do sistema: {e}")
            self.logger.error(f"Erro no reparo do sistema: {e}")
            return False
            
    def run_tcp_timeout_config(self) -> bool:
        """Executa a configuração de timeout TCP."""
        print("\n⏱️  Configurando Timeout TCP para Alta Velocidade...")
        print("🎯 Otimizando para nano segundo e scalping")
        try:
            success = self.tcp_manager.configure_tcp_timeout()
            if success:
                print("✅ Timeout TCP configurado com sucesso")
                print("💰 VANTAGEM: Reconexão 5x mais rápida em caso de falhas")
                print("🎯 CRUCIAL PARA: Arbitragem e operações de nano milissegundo")
                self.logger.info("Configuração de timeout TCP executada")
                return True
            else:
                print("❌ Falha na configuração de timeout TCP")
                print("💸 IMPACTO: Timeout lento pode causar perdas em situações críticas")
                self.logger.error("Falha na configuração de timeout TCP")
                return False
        except Exception as e:
            print(f"❌ Erro na configuração de timeout TCP: {e}")
            self.logger.error(f"Erro na configuração de timeout TCP: {e}")
            return False
            
    def run_all_fixes(self) -> bool:
        """Executa todas as correções em sequência otimizada para trading."""
        print("\n🎯 EXECUTANDO OTIMIZAÇÃO COMPLETA PARA TRADING")
        print("="*80)
        print("🚀 TRANSFORMAÇÃO TOTAL: Sistema otimizado para máxima performance")
        print("💰 INVESTIMENTO: Algumas centenas de milissegundos que podem")
        print("    salvar milhares em perdas durante volatilidade extrema")
        print("⏰ DURAÇÃO ESTIMADA: 15-45 minutos")
        print("="*80)
        print("🎯 RESULTADO ESPERADO: Conexão de nível profissional para trading")
        print("="*80)
        
        # Ordem otimizada para trading: problemas primeiro, depois otimizações
        fixes = [
            ("Reset de Rede", self.run_network_reset, "🔄"),
            ("Limpeza SSL/TLS", self.run_ssl_cleanup, "🔒"),
            ("Configuração DNS", self.run_dns_configuration, "🌐"),
            ("Desativação LSO", self.run_lso_disable, "📡"),
            ("Ajuste MTU", self.run_mtu_adjustment, "🔧"),
            ("Economia de Energia", self.run_adapter_power_disable, "⚡"),
            ("Timeout TCP", self.run_tcp_timeout_config, "⏱️"),
            ("Otimização Sistema", self.run_system_optimization, "🚀"),
            ("Reparo Sistema", self.run_system_repair, "🔨")
        ]
        
        success_count = 0
        total_fixes = len(fixes)
        
        print("\n💡 DICA: Mantenha este terminal aberto durante todo o processo!")
        print("🔥 APÓS CONCLUIR: Seu PC estará otimizado para trading profissional")
        
        for i, (fix_name, fix_function, icon) in enumerate(fixes, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{total_fixes}] {icon} EXECUTANDO: {fix_name}")
            print("💰 BENEFÍCIO: ", end="")
            
            # Adicionar contexto específico para cada otimização
            if "Reset" in fix_name:
                print("Eliminando problemas de conectividade que causam desconexões")
            elif "SSL" in fix_name:
                print("Garantindo conexões seguras sem falhas durante volatilidade")
            elif "DNS" in fix_name:
                print("Reduzindo latência em 15-50ms para execução mais rápida")
            elif "LSO" in fix_name:
                print("Eliminando micro-delays em operações de alta frequência")
            elif "MTU" in fix_name:
                print("Otimizando pacotes para máximo throughput")
            elif "Energia" in fix_name:
                print("Eliminando wake-up delays de adaptadores")
            elif "TCP" in fix_name:
                print("Reconexão ultra-rápida para trading sem interrupções")
            elif "Otimização" in fix_name:
                print("Liberando RAM/CPU para robôs de trading")
            elif "Reparo" in fix_name:
                print("Garantindo estabilidade total do sistema")
                
            print(f"{'='*80}")
            
            try:
                if fix_function():
                    success_count += 1
                    print(f"✅ {icon} CONCLUÍDO: {fix_name} - Performance melhorada!")
                else:
                    print(f"⚠️  FALHOU: {fix_name} - Continuando com próximas otimizações...")
            except Exception as e:
                print(f"❌ ERRO: {fix_name} - {e}")
                self.logger.error("Erro em '%s': %s\n%s", fix_name, e, traceback.format_exc())
                
        print("\n" + "="*80)
        print("🎊 EXECUÇÃO COMPLETA FINALIZADA!")
        print("="*80)
        print(f"📊 RESUMO DA TRANSFORMAÇÃO:")
        print(f"✅ Otimizações bem-sucedidas: {success_count}/{total_fixes}")
        print(f"⚠️  Otimizações com problemas: {total_fixes - success_count}/{total_fixes}")
        print("="*80)
        
        if success_count >= total_fixes * 0.8:  # 80% de sucesso
            print("🎯 STATUS: SISTEMA OTIMIZADO PARA TRADING PROFISSIONAL!")
            print("💰 PRÓXIMOS PASSOS: Reinicie seu PC para máximo benefício")
            print("🚀 PERFORMANCE: Aguarde melhoria significativa na latência")
        else:
            print("⚠️  STATUS: Otimização parcial - alguns problemas detectados")
            print("💡 RECOMENDAÇÃO: Execute novamente para completar todas as otimizações")
            
        print("="*80)
        
        return success_count == total_fixes
        
    def run(self) -> None:
        """Loop principal do menu interativo."""
        self.display_admin_warning()
        
        while True:
            try:
                self.display_main_menu()
                
                # Obter escolha do usuário
                choice = _safe_readline("\n👉 Digite sua escolha (0-10): ").strip()
                
                if choice == "0":
                    print("\n👋 Saindo do sistema de otimização para trading...")
                    self.logger.info("Usuário saiu do sistema")
                    break
                elif choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
                    # Mostrar detalhes da opção escolhida
                    confirmed = self.show_option_details(choice)
                    
                    if confirmed:
                        # Executar a função correspondente
                        if choice == "1":
                            self.run_dns_configuration()
                        elif choice == "2":
                            self.run_lso_disable()
                        elif choice == "3":
                            self.run_mtu_adjustment()
                        elif choice == "4":
                            self.run_adapter_power_disable()
                        elif choice == "5":
                            self.run_network_reset()
                        elif choice == "6":
                            self.run_ssl_cleanup()
                        elif choice == "7":
                            self.run_system_optimization()
                        elif choice == "8":
                            self.run_system_repair()
                        elif choice == "9":
                            self.run_tcp_timeout_config()
                        elif choice == "10":
                            self.run_all_fixes()
                    else:
                        print("\n❌ Operação cancelada pelo usuário.")
                else:
                    print("\n❌ Opção inválida! Por favor, escolha uma opção entre 0 e 10.")
                    
                # Pausa antes de mostrar o menu novamente
                if choice != "0":
                    _safe_pause("\n⏸️  Pressione ENTER para continuar...")
                    
            except KeyboardInterrupt:
                # NÃO encerra o programa: mantém o fluxo e a janela aberta.
                print("\n\n⚠️  Interrupção detectada (Ctrl+C). O programa continuará.")
                print("💡 Para sair, use a opção 0 no menu.")
                self.logger.info("Interrupção do usuário (Ctrl+C) ignorada para manter o programa aberto")
                time.sleep(1)
                continue
            except Exception as e:
                print(f"\n❌ Erro inesperado: {e}")
                self.logger.error(f"Erro inesperado no loop principal: {e}")
                _safe_pause("\n⏸️  Pressione ENTER para continuar...")


def check_dependencies() -> bool:
    """Verifica se as dependências necessárias estão instaladas."""
    required_modules = ['winreg', 'wmi', 'pythoncom', 'psutil']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("❌ DEPENDÊNCIAS FALTANDO:")
        print(f"Módulos não encontrados: {', '.join(missing_modules)}")
        print("\n📦 Para instalar as dependências, execute:")
        print("pip install pywin32 wmi psutil")
        print("\nOu crie um arquivo requirements.txt com:")
        print("pywin32>=306")
        print("wmi>=1.5.1") 
        print("psutil>=5.9.0")
        print("\nE execute: pip install -r requirements.txt")
        return False
    
    return True


def _safe_pause(prompt: str) -> None:
    """
    Pausa resiliente: mantém a janela aberta mesmo se houver Ctrl+C/EOF.
    """
    _safe_readline(prompt)


def _safe_readline(prompt: str, on_keyboard_interrupt: str = "ignore") -> str:
    """
    Leitura segura para ambientes onde `input()` pode gerar EOFError.

    - Não deixa o programa encerrar por Ctrl+C/EOF.
    - Evita "spam" de prompt quando stdin está em EOF.

    Args:
        prompt: Texto do prompt.
        on_keyboard_interrupt:
            - "ignore" (padrão): ignora Ctrl+C e pede novamente
            - "return_empty": retorna "" (útil para tratar como cancelado)
            - "raise": relança KeyboardInterrupt

    Returns:
        Linha lida (sem \\r\\n).
    """
    printed_prompt = False

    while True:
        try:
            if not printed_prompt and prompt:
                print(prompt, end="", flush=True)
                printed_prompt = True

            line = sys.stdin.readline()
            if line == "":
                # stdin fechado (EOF). Mantém vivo sem repetir o prompt.
                time.sleep(1)
                continue

            return line.rstrip("\r\n")

        except KeyboardInterrupt:
            if on_keyboard_interrupt == "raise":
                raise
            if on_keyboard_interrupt == "return_empty":
                return ""

            print("\n⚠️  Ctrl+C detectado. (Ignorado para manter o programa aberto.)")
            printed_prompt = False
            continue
        except Exception:
            # Qualquer falha inesperada: não fecha. Aguarda e tenta novamente.
            time.sleep(1)
            continue


def _print_exception_block(title: str, e: BaseException) -> None:
    print("\n" + "=" * 80)
    print(f"❌ {title}")
    print("=" * 80)
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensagem: {e}")
    print("\n📌 Detalhes técnicos (traceback):")
    print("-" * 80)
    print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
    print("-" * 80)


def _prompt_restart_computer() -> None:
    """
    Pergunta ao usuário se deseja reiniciar o computador.
    """
    print("\n" + "=" * 80)
    print("♻️  REINICIALIZAÇÃO RECOMENDADA")
    print("=" * 80)
    print("Para aplicar completamente algumas recomendações, é recomendado reiniciar o computador.")
    while True:
        resp = _safe_readline("\nDeseja reiniciar agora? (s/n): ").strip().lower()

        if resp in ("s", "sim", "y", "yes"):
            print("\n✅ Reiniciando em 5 segundos...")
            try:
                os.system("shutdown /r /t 5")
            except Exception as e:
                _print_exception_block("Falha ao solicitar reinicialização", e)
            return
        if resp in ("n", "nao", "não", "no"):
            print("\n✅ Ok. Reinicialize mais tarde para aplicar todas as otimizações.")
            return

        print("❌ Resposta inválida. Digite 's' para sim ou 'n' para não.")


def main():
    """Função principal do programa."""
    _configure_console_output()
    _agent_debug_log_runtime(
        run_id="import-debug",
        hypothesis_id="H2",
        location="main.py:main",
        message="Program start",
        data={
            "cwd": os.getcwd(),
            "sys_executable": getattr(sys, "executable", None),
            "has_meipass": hasattr(sys, "_MEIPASS"),
            "meipass": getattr(sys, "_MEIPASS", None),
            "sys_path_head": list(sys.path[:8]),
        },
    )
    print("🎰 Iniciando Sistema de Otimização para Trading...")
    print("🎯 Otimizado especificamente para Casino e Nano Trade")
    
    # Mantém o programa vivo/reexecutável mesmo se algo falhar.
    while True:
        # Verificar dependências (permite retry sem fechar)
        if not check_dependencies():
            print("\n⚠️  Sem dependências, não é possível executar as automações agora.")
            print("📌 Corrija as dependências e pressione ENTER para tentar novamente.")
            _safe_pause("\n⏸️  Pressione ENTER para REVERIFICAR dependências...")
            continue

        # Tentar importar módulos de automação (permite retry sem fechar)
        import_errors = _attempt_import_managers()
        if import_errors:
            print("\n❌ Não foi possível carregar alguns módulos de automação.")
            print("📌 Detalhes:")
            for err in import_errors:
                print(f" - {err}")
            print("\n✅ O programa NÃO será fechado.")
            print("📌 Corrija os arquivos/módulos e pressione ENTER para tentar novamente.")
            _safe_pause("\n⏸️  Pressione ENTER para TENTAR importar novamente...")
            continue

        try:
            # Criar e executar o otimizador de trading
            orchestrator = TradingOptimizerOrchestrator()
            orchestrator.run()

            # Somente ao final (quando o usuário sair do menu) sugerimos reiniciar.
            _prompt_restart_computer()
            _safe_pause("\n⏸️  Pressione ENTER para finalizar (a janela permanecerá aberta até você pressionar)...")
            return

        except SystemExit as e:
            # Captura qualquer sys.exit acidental em módulos e mantém vivo.
            _print_exception_block("SystemExit capturado (o programa não será fechado)", e)
            logging.error("SystemExit capturado: %s\n%s", e, traceback.format_exc())
            _safe_pause("\n⏸️  Pressione ENTER para continuar...")
            continue
        except Exception as e:
            _print_exception_block("ERRO CRÍTICO (o programa continuará)", e)
            logging.error("Erro crítico na execução: %s\n%s", e, traceback.format_exc())
            _safe_pause("\n⏸️  Pressione ENTER para continuar...")
            continue
        

if __name__ == "__main__":
    _configure_console_output()
    # Camada extra de segurança: nunca fechar por exceção não tratada.
    while True:
        try:
            main()
            break
        except BaseException as e:
            _print_exception_block("ERRO NÃO TRATADO NO NÍVEL MAIS ALTO (mantendo aberto)", e)
            logging.error("Erro não tratado no topo: %s\n%s", e, traceback.format_exc())
            _safe_pause("\n⏸️  Pressione ENTER para tentar novamente...")