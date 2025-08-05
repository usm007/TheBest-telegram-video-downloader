import os
import time
import sys
import traceback
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument, DocumentAttributeVideo
from colorama import init, Fore, Style

init(autoreset=True)

# 🎨 Fancy Print Functions
def print_header():
    print(Fore.CYAN + Style.BRIGHT + "\n██╗   ██╗███████╗███╗   ███╗ ██████╗  ██████╗ ███████╗")
    print(Fore.CYAN + Style.BRIGHT + "██║   ██║██╔════╝████╗ ████║██╔═████╗██╔═████╗╚════██║")
    print(Fore.CYAN + Style.BRIGHT + "██║   ██║███████╗██╔████╔██║██║██╔██║██║██╔██║    ██╔╝")
    print(Fore.CYAN + Style.BRIGHT + "██║   ██║╚════██║██║╚██╔╝██║████╔╝██║████╔╝██║   ██╔╝ ")
    print(Fore.CYAN + Style.BRIGHT + "╚██████╔╝███████║██║ ╚═╝ ██║╚██████╔╝╚██████╔╝   ██║  ")
    print(Fore.CYAN + Style.BRIGHT + " ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝    ╚═╝  " + Style.RESET_ALL)
    print(Fore.MAGENTA + Style.BRIGHT + "\n★ TELEGRAM VIDEO DOWNLOADER (CLI Edition) ★".center(60))
    print(Fore.CYAN + Style.BRIGHT + "-" * 60)

def print_success(msg):
    print(Fore.GREEN + "✅ " + msg)

def print_warning(msg):
    print(Fore.YELLOW + "⚠️  " + msg)

def print_error(msg):
    print(Fore.RED + "❌ " + msg)

# 📁 Create download folder
session_name = 'video_downloader'
download_folder = "downloads"
os.makedirs(download_folder, exist_ok=True)

# 🔐 Save/load credentials
def save_credentials(api_id, api_hash):
    with open("credentials.txt", "w") as f:
        f.write(f"{api_id}\n{api_hash}")

def load_credentials():
    if not os.path.exists("credentials.txt"):
        return None, None
    with open("credentials.txt", "r") as f:
        lines = f.readlines()
        return int(lines[0].strip()), lines[1].strip()

def human_readable(size):
    return f"{size / 1024 / 1024:.2f} MB"

async def download_with_progress(msg, file_path, file_size):
    print(Fore.MAGENTA + f"\n📥 Downloading: {os.path.basename(file_path)}")
    start_time = time.time()
    bytes_downloaded = 0
    last_update = time.time()

    def progress_callback(current, total):
        nonlocal bytes_downloaded, last_update
        bytes_downloaded = current
        now = time.time()
        if now - last_update > 0.3 or current == total:
            last_update = now
            percent = current / total * 100
            speed = current / (now - start_time + 1e-5)
            speed_mb = speed / (1024 * 1024)
            bar_length = 30
            filled = int(bar_length * current // total)
            bar = '█' * filled + '-' * (bar_length - filled)
            sys.stdout.write(f"\r{Fore.YELLOW}[{bar}] {percent:5.1f}% @ {speed_mb:.2f} MB/s")
            sys.stdout.flush()

    await msg.download_media(file=file_path, progress_callback=progress_callback)
    total_time = time.time() - start_time
    print_success(f"\n✅ Done: {os.path.basename(file_path)} ({human_readable(bytes_downloaded)} in {total_time:.1f}s)")

async def main():
    print_header()

    session_file = session_name + ".session"
    api_id, api_hash = load_credentials()

    if not os.path.exists(session_file) or api_id is None or api_hash is None:
        print(Fore.YELLOW + "\n🔑 First-time setup. Please enter your Telegram API credentials:")
        try:
            api_id = int(input("👉 Enter your API ID: ").strip())
            api_hash = input("👉 Enter your API Hash: ").strip()
            save_credentials(api_id, api_hash)
            phone = input("📱 Enter your phone number (with country code): ").strip()
        except Exception as e:
            print_error(f"Invalid input: {e}")
            return

        client = TelegramClient(session_name, api_id, api_hash)
        await client.start(phone)

    else:
        client = TelegramClient(session_name, api_id, api_hash)
        await client.start()

    async with client:
        print(Fore.BLUE + "\n📡 Fetching your dialogs (chats, channels, groups)...")
        dialogs = await client.get_dialogs()

        indexed_chats = []
        for i, dialog in enumerate(dialogs):
            name = dialog.name or "(No Name)"
            if dialog.is_channel or dialog.is_group or dialog.is_user:
                print(Fore.CYAN + f"[{i}] {name}")
                indexed_chats.append(dialog)

        try:
            choice = input(Fore.GREEN + "\n🔎 Select a chat number to scan for videos: ").strip()
            if not choice.isdigit():
                raise ValueError("Not a number.")
            idx = int(choice)
            if idx < 0 or idx >= len(indexed_chats):
                raise IndexError("Number out of range.")
            entity = indexed_chats[idx].entity
        except Exception as e:
            print_error(f"Invalid selection: {e}")
            return

        print(Fore.BLUE + f"\n📂 Scanning for videos in: {indexed_chats[idx].name}")
        messages = await client.get_messages(entity, limit=None)
        videos = []

        for msg in messages:
            try:
                if isinstance(msg.media, MessageMediaDocument):
                    doc = msg.media.document
                    is_video = any(isinstance(attr, DocumentAttributeVideo) for attr in doc.attributes)

                    if is_video:
                        # Safely extract filename
                        filename_attr = next(
                            (attr for attr in doc.attributes if hasattr(attr, 'file_name')),
                            None
                        )
                        file_name = filename_attr.file_name if filename_attr else f"video_{msg.id}.mp4"
                        name = f"{msg.id}_{file_name}"
                        size_mb = doc.size / 1024 / 1024
                        videos.append({"msg": msg, "name": name, "size": size_mb})
            except Exception as e:
                print_warning(f"⚠️ Skipped a message (ID: {getattr(msg, 'id', 'N/A')}) due to error: {e}")
                continue

        if not videos:
            print_warning("No videos found in this chat.")
            return

        print(Fore.CYAN + f"\n📼 Found {len(videos)} videos:")
        for i, vid in enumerate(videos):
            print(Fore.YELLOW + f"[{i}] {vid['name']} ({vid['size']:.2f} MB)")

        indexes = input(Fore.GREEN + "\n🎯 Enter video numbers to download (comma-separated): ")
        try:
            selected = [videos[int(i.strip())] for i in indexes.split(',')]
        except (IndexError, ValueError):
            print_error("Invalid selection.")
            return

        print_header()
        for vid in selected:
            path = os.path.join(download_folder, vid["name"])
            await download_with_progress(vid["msg"], path, vid["size"] * 1024 * 1024)

        print_success(f"\n📁 All downloads complete. Saved in '{download_folder}'.")

# 🚨 Global Crash Logger
if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"crash_log_{timestamp}.txt"
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("❌ TELEGRAM VIDEO DOWNLOADER - CRASH LOG\n")
            f.write(f"🕒 Timestamp: {timestamp}\n")
            f.write(f"💥 Exception Type: {type(e).__name__}\n")
            f.write(f"📝 Error Message: {str(e)}\n\n")
            f.write("🔍 Full Traceback:\n")
            f.write(traceback.format_exc())
        print_error(f"\n💀 The script crashed. Details saved in '{log_filename}'.")
