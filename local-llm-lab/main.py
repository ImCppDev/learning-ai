import argparse
import time

from colorama import Fore, Style, init as colorama_init
from openai import OpenAI

PROVIDERS = {
    "ollama": {"base_url": "http://127.0.0.1:11434/v1",
               "api_key": "ollama",
               "model": "llama3.1:8b"},
    "lmstudio": {"base_url": "http://127.0.0.1:1234/v1",
                 "api_key": "lm-studio",
                 "model": "qwen/qwen3.5-9b"},
}

EXIT_COMMANDS = {"exit", "quit", "выход"}


def ask(client, model, question):
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
        stream=True,
    )

    tokens = 0
    start = time.perf_counter()
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            tokens += 1
            print(f"{Fore.GREEN}{delta}{Style.RESET_ALL}", end="", flush=True)
    elapsed = time.perf_counter() - start

    print()
    if elapsed > 0:
        print(f"{Fore.YELLOW}[{tokens} tok, {tokens / elapsed:.2f} tok/sec]{Style.RESET_ALL}")


def main():
    parser = argparse.ArgumentParser(description="Простой чат-клиент для локальных LLM")
    parser.add_argument("--provider", choices=PROVIDERS.keys(), default="lmstudio",
                         help="Провайдер (по умолчанию: lmstudio)")
    parser.add_argument("--model", help="Имя модели (по умолчанию берётся из настроек провайдера)")
    args = parser.parse_args()

    colorama_init()

    cfg = PROVIDERS[args.provider]
    model = args.model or cfg["model"]
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])

    print(f"Провайдер: {args.provider}, модель: {model}")
    print(f"Для выхода введите: {', '.join(EXIT_COMMANDS)}\n")

    while True:
        question = input(f"{Fore.CYAN}Вы: {Style.RESET_ALL}")
        if question.strip().lower() in EXIT_COMMANDS:
            break
        ask(client, model, question)
        print()


if __name__ == "__main__":
    main()
