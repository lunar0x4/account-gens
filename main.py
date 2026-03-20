import os
import sys
import subprocess
from colorama import init, Fore

init(autoreset=True)

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_banner():
    print(f"{Fore.CYAN}{'='*30}")
    print(f"{Fore.CYAN}ACCOUNT GENERATOR LOADER")
    print(f"{Fore.YELLOW}created by lunar0x4")
    print(f"{Fore.CYAN}{'='*30}\n")

def main():
    clear_screen()
    print_banner()

    print(f"{Fore.GREEN}[1] {Fore.WHITE}hyper3d.ai")
    print(f"{Fore.CYAN}[1] {Fore.WHITE}piclumen.py")
    print(f"{Fore.RED}[0] {Fore.WHITE}exit\n")

    try:
        choice = input(f"{Fore.CYAN}select an option: {Fore.WHITE}")

        if choice == "1":
            subprocess.run([sys.executable, "gens/hyper3d.py"])
        elif choice == "2":
            subprocess.run([sys.executable, "gens/piclumen.py"])
        elif choice == "0":
            print(f"\n{Fore.GREEN}goodbye!")
            sys.exit(0)
        else:
            print(f"\n{Fore.RED}invalid option!")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n\n{Fore.GREEN}goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
