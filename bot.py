import asyncio
import os
import random
from pathlib import Path

import discord
from discord import app_commands

BASE_DIR = Path(__file__).resolve().parent
NGON_FILE = BASE_DIR / "ngon_da_them_hash.txt"

OWNER_ID = 1417497667449126952

ADMIN_IDS = {
    1417497667449126952,
    1330425526363623494,
}

MIN_INTERVAL = 0.1

loop_tasks: dict[int, list[asyncio.Task]] = {}
ngon_tasks: dict[int, list[asyncio.Task]] = {}
ngon_queues: dict[int, list[str]] = {}


def load_ngon() -> list[str]:
    try:
        if not NGON_FILE.exists():
            print(f"[NGON] KHÔNG TÌM THẤY: {NGON_FILE}")
            return []

        with NGON_FILE.open("r", encoding="utf-8-sig") as f:
            lines = [line.strip() for line in f if line.strip()]

        print(f"[NGON] Đã đọc được {len(lines)} dòng")
        return lines

    except Exception as e:
        print(f"[NGON] Lỗi: {e}")
        return []


def get_next_ngon(channel_id: int) -> str | None:
    queue = ngon_queues.get(channel_id)

    if not queue:
        data = load_ngon()
        if not data:
            return None

        queue = data.copy()
        random.shuffle(queue)
        ngon_queues[channel_id] = queue

    return queue.pop()


async def admin_only(interaction: discord.Interaction) -> bool:
    if interaction.user.id == OWNER_ID:
        return True

    if interaction.user.id in ADMIN_IDS:
        return True

    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ Bạn không có quyền dùng lệnh này."
        )
    return False


intents = discord.Intents.default()
client = discord.Client(intents=intents)

tree = app_commands.CommandTree(
    client,
    allowed_installs=app_commands.AppInstallationType(
        guild=True,
        user=True,
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
        print("=" * 50)
        print(f"🤖 Bot: {client.user}")
        print(f"🆔 ID: {client.user.id}")
        print(f"🌍 Đang ở {len(client.guilds)} server")
        print(f"📜 Global slash commands: {len(synced)}")
        print("=" * 50)
    except Exception:
        import traceback
        print("[SYNC ERROR]")
        traceback.print_exc()


@tree.command(name="add", description="Thêm người dùng làm admin")
@app_commands.describe(user="Người dùng muốn cấp quyền")
async def add(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Chỉ boss mới cấp quyền."
        )
        return

    if user.id in ADMIN_IDS:
        await interaction.response.send_message(
            f"⚠️ {user.mention} đã là admin."
        )
        return

    ADMIN_IDS.add(user.id)

    await interaction.response.send_message(
        f"✅ Đã thêm {user.mention} làm admin."
    )


@tree.command(name="listadmin", description="Xem danh sách admin bot")
async def listadmin(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    lines = []
    for user_id in sorted(ADMIN_IDS):
        user = client.get_user(user_id)
        if user:
            lines.append(f"• {user.mention} ({user.id})")
        else:
            lines.append(f"• User ID: {user_id}")

    if not lines:
        lines.append("• Chưa có admin nào.")

    await interaction.response.send_message(
        "👑 **Danh sách Admin**\n\n" + "\n".join(lines)
    )


@tree.command(name="removeadmin", description="Xóa quyền admin của người dùng")
@app_commands.describe(user="Người dùng muốn xóa quyền")
async def removeadmin(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Chỉ boss mới thu quyền."
        )
        return

    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Không thể tự xóa quyền của chính mình."
        )
        return

    if user.id not in ADMIN_IDS:
        await interaction.response.send_message(
            f"⚠️ {user.mention} không phải admin."
        )
        return

    ADMIN_IDS.remove(user.id)

    await interaction.response.send_message(
        f"✅ Đã xóa quyền admin của {user.mention}."
    )


@tree.command(name="servers", description="Xem các server bot đang ở")
async def servers(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Chỉ boss mới xem được."
        )
        return

    if not client.guilds:
        await interaction.response.send_message(
            "ℹ️ User Install không cung cấp danh sách server cho bot theo cách này."
        )
        return

    lines = [
        f"**{g.name}**\nID: `{g.id}` | Thành viên: {g.member_count}"
        for g in client.guilds
    ]

    await interaction.response.send_message(
        "## 🌍 Danh sách server\n\n" + "\n\n".join(lines)
    )


@tree.command(name="startsay", description="Bật gửi tin định kỳ")
@app_commands.describe(
    message="Nội dung muốn gửi",
    seconds="Khoảng cách giữa các lần gửi (tối thiểu 0.1)",
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

    if seconds < MIN_INTERVAL:
        seconds = MIN_INTERVAL

    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message(
            "❌ Không xác định được channel."
        )
        return

    channel_id = interaction.channel_id

    await interaction.response.send_message(
        f"✅ Đã bật gửi tin mỗi {seconds:g} giây."
        + (f" Tag {user.mention}." if user else "")
    )

    async def sender():
        while True:
            try:
                content = f"{message} {user.mention}" if user else message
                await channel.send(
                    content,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
                await asyncio.sleep(seconds)

            except asyncio.CancelledError:
                raise

            except discord.HTTPException as e:
                print(f"[DISCORD ERROR] startsay: {e}")
                await asyncio.sleep(max(seconds, MIN_INTERVAL))

            except Exception as e:
                print(f"[ERROR] startsay: {e}")
                await asyncio.sleep(max(seconds, MIN_INTERVAL))

    task = asyncio.create_task(sender())
    loop_tasks.setdefault(channel_id, []).append(task)


@tree.command(name="stopsay", description="Tắt tất cả gửi tin định kỳ trong kênh")
async def stopsay(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    channel_id = interaction.channel_id
    tasks_list = loop_tasks.pop(channel_id, None)

    if tasks_list:
        for task in tasks_list:
            task.cancel()

        await interaction.response.send_message(
            "✅ Đã tắt tất cả loop trong channel này."
        )
    else:
        await interaction.response.send_message(
            "ℹ️ Channel này không có loop nào đang chạy."
        )


@tree.command(name="startngon", description="Đọc lần lượt các dòng từ file")
@app_commands.describe(
    seconds="Khoảng cách giữa các lần gửi (tối thiểu 0.1)",
    user="Người dùng muốn tag (không bắt buộc)",
)
async def startngon(
    interaction: discord.Interaction,
    seconds: float = MIN_INTERVAL,
    user: discord.User | None = None,
):
    if not await admin_only(interaction):
        return

    if seconds < MIN_INTERVAL:
        seconds = MIN_INTERVAL

    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message(
            "❌ Không xác định được channel."
        )
        return

    channel_id = interaction.channel_id

    if not load_ngon():
        await interaction.response.send_message(
            "❌ File không tồn tại hoặc không có dòng nào."
        )
        return

    await interaction.response.send_message(
        f"✅ Đã bắt đầu đọc file mỗi {seconds:g} giây."
        + (f" Tag {user.mention}." if user else "")
    )

    async def ngon_sender():
        while True:
            try:
                line = get_next_ngon(channel_id)
                if line is None:
                    await asyncio.sleep(seconds)
                    continue

                content = line
                if user:
                    content += f" {user.mention}"

                await channel.send(
                    content,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
                await asyncio.sleep(seconds)

            except asyncio.CancelledError:
                raise

            except discord.HTTPException as e:
                print(f"[NGON DISCORD ERROR] {e}")
                await asyncio.sleep(max(seconds, MIN_INTERVAL))

            except Exception as e:
                print(f"[ERROR] startngon: {e}")
                await asyncio.sleep(max(seconds, MIN_INTERVAL))

    task = asyncio.create_task(ngon_sender())
    ngon_tasks.setdefault(channel_id, []).append(task)


@tree.command(name="stopngon", description="Dừng tất cả vòng đọc file trong kênh")
async def stopngon(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    channel_id = interaction.channel_id
    tasks_list = ngon_tasks.pop(channel_id, None)

    if tasks_list:
        for task in tasks_list:
            task.cancel()

        await interaction.response.send_message(
            "✅ Đã dừng tất cả vòng đọc file trong channel này."
        )
    else:
        await interaction.response.send_message(
            "ℹ️ Channel này không có vòng đọc file nào."
        )


@client.event
async def on_error(event, *args, **kwargs):
    import traceback
    print(f"[EVENT ERROR] {event}")
    traceback.print_exc()


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Chưa đặt biến môi trường DISCORD_TOKEN trên Render."
    )

print("=== TEST FILE NGON ===")
print("Đường dẫn:", NGON_FILE)
print("Tồn tại:", NGON_FILE.exists())
print("Số dòng:", len(load_ngon()))
print("======================")

client.run(TOKEN)
