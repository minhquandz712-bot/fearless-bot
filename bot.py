import asyncio
import os
import random
import traceback
from pathlib import Path

import discord
from discord import app_commands

# =========================================================
# CẤU HÌNH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
NGON_FILE = BASE_DIR / "ngon_da_them_hash.txt"

OWNER_ID = 1417497667449126952

# DANH SÁCH ĐƯỢC PHÉP VĨNH VIỄN
# CHỈ 3 Discord ID này được phép dùng bot.
# Không có /add hoặc /removeadmin để cấp quyền từ Discord.
ADMIN_IDS = {
    1417497667449126952,
    1330425526363623494,
    1523592473916608643,
}

# Giữ 0.1 để không tự ý đổi cách bạn đang dùng.
# Discord vẫn có rate-limit; nếu gửi quá nhanh thì Discord có thể chặn tạm thời.
MIN_INTERVAL = 0.1

# Mỗi channel chỉ chạy tối đa 1 loop / loại.
say_tasks: dict[int, asyncio.Task] = {}
ngon_tasks: dict[int, asyncio.Task] = {}

# Queue riêng cho từng channel để startngon không bị lặp lại một dòng
# cho tới khi đã chạy hết danh sách.
ngon_queues: dict[int, list[str]] = {}


# =========================================================
# FILE NGON
# =========================================================

def load_ngon() -> list[str]:
    """Đọc toàn bộ dòng không rỗng từ ngon_da_them_hash.txt."""
    try:
        if not NGON_FILE.exists():
            print(f"[NGON] Không tìm thấy file: {NGON_FILE}")
            return []

        with NGON_FILE.open("r", encoding="utf-8-sig") as f:
            lines = [line.strip() for line in f if line.strip()]

        print(f"[NGON] Đã đọc {len(lines)} dòng")
        return lines

    except Exception:
        print("[NGON] Lỗi khi đọc file:")
        traceback.print_exc()
        return []


def get_next_ngon(channel_id: int) -> str | None:
    """
    Lấy dòng tiếp theo.
    Hết queue thì đọc lại file và xáo trộn một vòng mới.
    """
    queue = ngon_queues.get(channel_id)

    if not queue:
        data = load_ngon()
        if not data:
            return None

        queue = data.copy()
        random.shuffle(queue)
        ngon_queues[channel_id] = queue

    return queue.pop()


# =========================================================
# QUYỀN
# =========================================================

async def admin_only(interaction: discord.Interaction) -> bool:
    # CHỈ 3 ID trong ADMIN_IDS được phép dùng bot.
    if interaction.user.id in ADMIN_IDS:
        return True

    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ Bạn không có quyền dùng bot này.",
            ephemeral=True,
        )

    return False


def is_server_installed() -> bool:
    """
    Với Guild Install, client.guilds sẽ có guild đó.
    User Install có thể vẫn nhận interaction nhưng không có quyền
    hành động như một bot thành viên trong server.
    """
    return True


async def require_guild_install(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Lệnh này cần dùng trong server.",
            ephemeral=True,
        )
        return False

    if interaction.guild.id not in {g.id for g in client.guilds}:
        await interaction.response.send_message(
            "❌ FEARLESS đang được dùng dưới dạng User Install.\n"
            "Hãy cài FEARLESS vào **server (Guild Install)** để bot có quyền gửi tin nhắn.",
            ephemeral=True,
        )
        return False

    return True


# =========================================================
# DISCORD CLIENT
# =========================================================

intents = discord.Intents.default()
client = discord.Client(intents=intents)

tree = app_commands.CommandTree(
    client,
    allowed_installs=app_commands.AppInstallationType(
        guild=True,
        user=False,
    ),
    allowed_contexts=app_commands.AppCommandContext(
        guild=True,
        dm_channel=True,
        private_channel=True,
    ),
)


@client.event
async def on_ready():
    try:
        synced = await tree.sync()

        print("=" * 60)
        print(f"🤖 Bot: {client.user}")
        print(f"🆔 ID: {client.user.id}")
        print(f"🌍 Server: {len(client.guilds)}")
        print(f"📜 Slash commands: {len(synced)}")
        print("=" * 60)

    except Exception:
        print("[SYNC ERROR]")
        traceback.print_exc()


# =========================================================
# ADMIN
# =========================================================

@tree.command(name="listadmin", description="Xem danh sách admin bot")
async def listadmin(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    lines = []

    for user_id in sorted(ADMIN_IDS):
        user = client.get_user(user_id)

        if user:
            lines.append(f"• {user.mention} (`{user.id}`)")
        else:
            lines.append(f"• User ID: `{user_id}`")

    if not lines:
        lines.append("• Chưa có admin nào.")

    await interaction.response.send_message(
        "👑 **Danh sách Admin**\n\n" + "\n".join(lines),
        ephemeral=True,
    )


@tree.command(name="servers", description="Xem các server bot đang ở")
async def servers(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    if not client.guilds:
        await interaction.response.send_message(
            "ℹ️ FEARLESS hiện chưa được cài vào server nào.",
            ephemeral=True,
        )
        return

    lines = []

    for guild in client.guilds:
        lines.append(
            f"**{guild.name}**\n"
            f"ID: `{guild.id}` | Thành viên: {guild.member_count}"
        )

    await interaction.response.send_message(
        "## 🌍 Server FEARLESS đang ở\n\n" + "\n\n".join(lines),
        ephemeral=True,
    )


# =========================================================
# STARTSAY
# =========================================================

@tree.command(name="startsay", description="Bật gửi tin định kỳ trong channel hiện tại")
@app_commands.describe(
    message="Nội dung muốn gửi",
    seconds="Khoảng cách giữa các lần gửi",
    user="Người dùng muốn tag (không bắt buộc)",
)
async def startsay(
    interaction: discord.Interaction,
    message: str,
    seconds: float,
    user: discord.User | None = None,
):
    if not await admin_only(interaction):
        return

    if not await require_guild_install(interaction):
        return

    seconds = max(float(seconds), MIN_INTERVAL)

    channel = interaction.channel

    if channel is None:
        await interaction.response.send_message(
            "❌ Không xác định được channel.",
            ephemeral=True,
        )
        return

    channel_id = interaction.channel_id

    # Nếu channel đang có startsay, dừng loop cũ trước.
    old_task = say_tasks.pop(channel_id, None)

    if old_task:
        old_task.cancel()

    await interaction.response.send_message(
        f"✅ Đã bật gửi tin mỗi **{seconds:g} giây**."
        + (f" Tag {user.mention}." if user else "")
    )

    async def sender():
        try:
            while True:
                content = message

                if user:
                    content += f" {user.mention}"

                try:
                    await channel.send(
                        content,
                        allowed_mentions=discord.AllowedMentions(
                            users=True
                        ),
                    )
                except discord.Forbidden:
                    print(
                        f"[STARTSAY] Không có quyền gửi tin trong channel "
                        f"{channel_id}."
                    )
                    break
                except discord.HTTPException as e:
                    print(f"[STARTSAY HTTP ERROR] {e}")
                except Exception:
                    print("[STARTSAY ERROR]")
                    traceback.print_exc()

                await asyncio.sleep(seconds)

        except asyncio.CancelledError:
            raise
        finally:
            current = say_tasks.get(channel_id)

            if current is asyncio.current_task():
                say_tasks.pop(channel_id, None)

    task = asyncio.create_task(sender())
    say_tasks[channel_id] = task


# =========================================================
# STOPSAY
# =========================================================

@tree.command(name="stopsay", description="Tắt gửi tin định kỳ trong channel hiện tại")
async def stopsay(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    channel_id = interaction.channel_id
    task = say_tasks.pop(channel_id, None)

    if task:
        task.cancel()

        await interaction.response.send_message(
            "✅ Đã tắt startsay trong channel này."
        )
    else:
        await interaction.response.send_message(
            "ℹ️ Channel này không có startsay đang chạy.",
            ephemeral=True,
        )


# =========================================================
# STARTNGON
# =========================================================

@tree.command(name="startngon", description="Gửi lần lượt các dòng trong ngon_da_them_hash.txt")
@app_commands.describe(
    seconds="Khoảng cách giữa các lần gửi",
    user="Người dùng muốn tag (không bắt buộc)",
)
async def startngon(
    interaction: discord.Interaction,
    seconds: float = MIN_INTERVAL,
    user: discord.User | None = None,
):
    if not await admin_only(interaction):
        return

    if not await require_guild_install(interaction):
        return

    seconds = max(float(seconds), MIN_INTERVAL)

    channel = interaction.channel

    if channel is None:
        await interaction.response.send_message(
            "❌ Không xác định được channel.",
            ephemeral=True,
        )
        return

    channel_id = interaction.channel_id

    if not load_ngon():
        await interaction.response.send_message(
            "❌ `ngon_da_them_hash.txt` không tồn tại hoặc không có dòng nào.",
            ephemeral=True,
        )
        return

    # Dừng vòng ngon cũ trong channel nếu có.
    old_task = ngon_tasks.pop(channel_id, None)

    if old_task:
        old_task.cancel()

    # Bắt đầu một vòng dữ liệu mới.
    ngon_queues[channel_id] = []

    await interaction.response.send_message(
        f"✅ Đã bắt đầu đọc `ngon_da_them_hash.txt` mỗi **{seconds:g} giây**."
        + (f" Tag {user.mention}." if user else "")
    )

    async def sender():
        try:
            while True:
                line = get_next_ngon(channel_id)

                if line is None:
                    print("[STARTNGON] Không còn dữ liệu.")
                    break

                content = line

                if user:
                    content += f" {user.mention}"

                try:
                    await channel.send(
                        content,
                        allowed_mentions=discord.AllowedMentions(
                            users=True
                        ),
                    )
                except discord.Forbidden:
                    print(
                        f"[STARTNGON] Không có quyền gửi tin trong channel "
                        f"{channel_id}."
                    )
                    break
                except discord.HTTPException as e:
                    print(f"[STARTNGON HTTP ERROR] {e}")
                except Exception:
                    print("[STARTNGON ERROR]")
                    traceback.print_exc()

                await asyncio.sleep(seconds)

        except asyncio.CancelledError:
            raise
        finally:
            current = ngon_tasks.get(channel_id)

            if current is asyncio.current_task():
                ngon_tasks.pop(channel_id, None)

    task = asyncio.create_task(sender())
    ngon_tasks[channel_id] = task


# =========================================================
# STOPNGON
# =========================================================

@tree.command(name="stopngon", description="Dừng đọc ngon_da_them_hash.txt")
async def stopngon(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    channel_id = interaction.channel_id
    task = ngon_tasks.pop(channel_id, None)

    if task:
        task.cancel()
        ngon_queues.pop(channel_id, None)

        await interaction.response.send_message(
            "✅ Đã dừng startngon trong channel này."
        )
    else:
        await interaction.response.send_message(
            "ℹ️ Channel này không có startngon đang chạy.",
            ephemeral=True,
        )


# =========================================================
# LỖI
# =========================================================

@client.event
async def on_error(event, *args, **kwargs):
    print(f"[EVENT ERROR] {event}")
    traceback.print_exc()


# =========================================================
# CHẠY BOT
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Chưa đặt biến môi trường DISCORD_TOKEN trên Render."
    )

print("=== FEARLESS STARTUP ===")
print(f"NGON FILE: {NGON_FILE}")
print(f"NGON FILE EXISTS: {NGON_FILE.exists()}")
print(f"NGON LINES: {len(load_ngon())}")
print("========================")

client.run(TOKEN)
