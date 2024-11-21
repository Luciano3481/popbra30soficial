import requests
import time

# URL da API
url = 'https://22885.club/api/webapi/GetNoaverageEmerdList'

# Cabeçalhos da requisição
headers = {
    'authority': '22885.club',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'pt-BR,pt;q=0.9',
    'content-type': 'application/json;charset=UTF-8',
    'origin': 'https://www.popbra.com',
    'referer': 'https://www.popbra.com/',
    'sec-ch-ua': '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 Edg/130.0.0.0'
}

# Payload da requisição
payload = {
    "pageSize": 10,
    "pageNo": 1,
    "typeId": 30,
    "language": 3,
    "random": "acf07dd76c5c499c837f89d72d51be5c",
    "signature": "A14419DFD4F4BF3A384273EEDBD524BD",
    "timestamp": 1731108877
}

# Variável global para controlar o último período processado
ultimo_periodo = None
# Dicionário para armazenar as IDs das mensagens enviadas
message_ids = {}
# Variável global para indicar se há uma entrada em andamento
entrada_em_andamento = False

# Função para fazer a requisição à API
def fetch_data():
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # Lança erro para códigos 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados da API: {e}")
        return None

# Função para determinar o "Tamanho" baseado no número
def determinar_tamanho(number):
    try:
        numero = int(number)
        if 0 <= numero <= 4:
            return "Pequeno"
        elif 5 <= numero <= 9:
            return "Grande"
        return "Desconhecido"
    except ValueError:
        return "Erro"

# Estruturas de estratégias com entrada e gales
estrategias = [
    {
        "estrategia": ["Grande", "Pequeno", "Grande", "Pequeno"],
        "entrada": "Pequeno",
        "gales": ["Pequeno", "Grande", "Grande"]
    },
    {
        "estrategia": ["Grande", "Pequeno", "Pequeno", "Pequeno", "Grande"],
        "entrada": "Grande",
        "gales": ["Pequeno", "Pequeno", "Pequeno"]
    },
    {
        "estrategia": ["Pequeno", "Grande", "Grande", "Grande", "Pequeno"],
        "entrada": "Pequeno",
        "gales": ["Grande", "Grande", "Grande"]
    },
    {
        "estrategia": ["Grande", "Grande", "Grande", "Grande"],
        "entrada": "Grande",
        "gales": ["Pequeno", "Grande", "Pequeno"]
    },
    {
        "estrategia": ["Pequeno", "Pequeno", "Pequeno", "Pequeno"],
        "entrada": "Pequeno",
        "gales": ["Grande", "Pequeno", "Grande"]
    },
    {
        "estrategia": ["Pequeno", "Grande", "Pequeno", "Pequeno"],
        "entrada": "Grande",
        "gales": ["Grande", "Pequeno", "Pequeno"]
    },
    {
        "estrategia": ["Pequeno", "Grande", "Pequeno", "Grande"],
        "entrada": "Grande",
        "gales": ["Grande", "Pequeno", "Pequeno"]
    },
    {
        "estrategia": ["Grande", "Grande", "Pequeno", "Pequeno"],
        "entrada": "Pequeno",
        "gales": ["Grande", "Grande", "Pequeno"]
    },
    {
        "estrategia": ["Pequeno", "Pequeno", "Grande", "Grande"],
        "entrada": "Grande",
        "gales": ["Pequeno", "Pequeno", "Grande"]
    }
]

# Função para processar dados com verificação de mudança de período
def processar_dados(data, grupo_telegram_id, token_telegram, thread_id):
    entries = data['data']['list']
    periodos = []
    tamanhos = []

    # Processando os dados da resposta
    for entry in entries:
        periodo = entry['issueNumber'][-5:]  # Últimos 5 caracteres como período
        tamanho = determinar_tamanho(entry['number'])
        periodos.append(periodo)
        tamanhos.append(tamanho)

    # Monitorando mudanças de período
    global ultimo_periodo, entrada_em_andamento
    if periodos[0] == ultimo_periodo and entrada_em_andamento:
        return
    else:
        ultimo_periodo = periodos[0]

    # Iterando sobre as estratégias
    for estrategia in estrategias:
        estrategia_str = ",".join(estrategia['estrategia'])
        tamanhos_str = ",".join(tamanhos[:len(estrategia['estrategia'])])

        if tamanhos_str == estrategia_str:
            proximo_periodo = str(int(periodos[0]) + 1)
            enviar_entrada(grupo_telegram_id, token_telegram, estrategia['entrada'], proximo_periodo, thread_id)
            entrada_em_andamento = True
            esperar_resultado(tamanhos, estrategia, grupo_telegram_id, token_telegram, thread_id)

# Função para aguardar e verificar o resultado antes de ativar Gales
def esperar_resultado(tamanhos, estrategia, grupo_telegram_id, token_telegram, thread_id):
    global ultimo_periodo
    while True:
        nova_data = fetch_data()
        if nova_data and 'data' in nova_data and 'list' in nova_data['data']:
            novos_periodos = [entry['issueNumber'][-5:] for entry in nova_data['data']['list']]
            novos_tamanhos = [
                determinar_tamanho(entry['number']) for entry in nova_data['data']['list']
            ]

            if novos_periodos[0] != ultimo_periodo:
                ultimo_periodo = novos_periodos[0]
                apagar_mensagens_anteriores(grupo_telegram_id, token_telegram, thread_id)

                if novos_tamanhos[0] == estrategia['entrada']:
                    print(f"✅✅✅")
                    enviar_sucesso(grupo_telegram_id, token_telegram, thread_id)
                    return
                else:
                    ativar_gales(novos_tamanhos, estrategia['gales'], grupo_telegram_id, token_telegram, thread_id)
                break
        else:
            print("Erro ao buscar novos dados ou dados inválidos. Tentando novamente...")
        time.sleep(2)

# Função para ativar os gales
def ativar_gales(tamanhos, gales, grupo_telegram_id, token_telegram, thread_id):
    global ultimo_periodo
    for i, gale in enumerate(gales, 1):
        print(f"Ativando Gale {i}: {gale}")
        apagar_mensagens_anteriores(grupo_telegram_id, token_telegram, thread_id)
        enviar_gale(grupo_telegram_id, token_telegram, i, gale, thread_id)
        time.sleep(2)

        while True:
            nova_data = fetch_data()
            if nova_data and 'data' in nova_data and 'list' in nova_data['data']:
                novos_periodos = [entry['issueNumber'][-5:] for entry in nova_data['data']['list']]
                novos_tamanhos = [
                    determinar_tamanho(entry['number']) for entry in nova_data['data']['list']
                ]

                if novos_periodos[0] != ultimo_periodo:
                    ultimo_periodo = novos_periodos[0]
                    apagar_mensagens_anteriores(grupo_telegram_id, token_telegram, thread_id)

                    if novos_tamanhos[0] == gale:
                        print(f"✅✅✅")
                        enviar_sucesso(grupo_telegram_id, token_telegram, thread_id)
                        return
                    break
            time.sleep(2)

    print("🔴Todos os gales falharam.🔴")
    enviar_falha(grupo_telegram_id, token_telegram, thread_id)

# Funções para envio ao Telegram
def enviar_entrada(grupo_telegram_id, token_telegram, entrada, proximo_periodo, thread_id):
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    cor = "🔵" if entrada == "Pequeno" else "🟠"
    mensagem = (
        f"*✅ENTRADA IDENTIFICADA✅*\n"  # Texto em negrito
        f"👉*Apostar:* {entrada}{cor}\n"  # Texto em negrito
        f"🕗*Período:* {proximo_periodo}\n"  # Texto em negrito
        f"🛡Máximo 3 Gales🛡"
    )
    payload = {
        "chat_id": grupo_telegram_id,
        "text": mensagem,
        "message_thread_id": thread_id,
        "parse_mode": "MarkdownV2"  # Especifica o uso de MarkdownV2 para formatação
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        message_ids["last_message_id"] = response.json()["result"]["message_id"]


def enviar_gale(grupo_telegram_id, token_telegram, gale_num, gale, thread_id):
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    mensagem = f"Gale {gale_num}: Faça a aposta em {gale}"
    payload = {
        "chat_id": grupo_telegram_id,
        "text": mensagem,
        "message_thread_id": thread_id
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        message_ids[f"gale_{gale_num}"] = response.json()["result"]["message_id"]

def enviar_sucesso(grupo_telegram_id, token_telegram, thread_id):
    global entrada_em_andamento
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    mensagem = "✅✅✅"
    payload = {
        "chat_id": grupo_telegram_id,
        "text": mensagem,
        "message_thread_id": thread_id
    }
    response = requests.post(url, data=payload)
    entrada_em_andamento = False  # Redefine a variável para permitir novas entradas
    # Enviar novo sinal imediatamente após o sucesso
    nova_data = fetch_data()
    if nova_data:
        processar_dados(nova_data, grupo_telegram_id, token_telegram, thread_id)

def enviar_falha(grupo_telegram_id, token_telegram, thread_id):
    global entrada_em_andamento
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    mensagem = "❌❌❌"
    payload = {
        "chat_id": grupo_telegram_id,
        "text": mensagem,
        "message_thread_id": thread_id
    }
    response = requests.post(url, data=payload)
    entrada_em_andamento = False  # Redefine a variável para permitir novas entradas
    # Enviar novo sinal imediatamente após a falha
    nova_data = fetch_data()
    if nova_data:
        processar_dados(nova_data, grupo_telegram_id, token_telegram, thread_id)

def apagar_mensagens_anteriores(grupo_telegram_id, token_telegram, thread_id):
    global message_ids
    if ultimo_periodo is not None:
        for key in list(message_ids.keys()):
            if key != "last_message_id":
                message_id = message_ids[key]
                url = f"https://api.telegram.org/bot{token_telegram}/deleteMessage"
                payload = {
                    "chat_id": grupo_telegram_id,
                    "message_id": message_id,
                    "message_thread_id": thread_id
                }
                response = requests.post(url, data=payload)

        message_ids = {"last_message_id": message_ids.get("last_message_id")}

def main():
    grupo_telegram_id = "-1002264134019"
    token_telegram = "7225969674:AAGEBR-Z8y8Zl97MJgazcIeUugIu7a2B85E"
    thread_id = 0

    while True:
        data = fetch_data()
        if data:
            processar_dados(data, grupo_telegram_id, token_telegram, thread_id)
        time.sleep(2)

if __name__ == "__main__":
    main()