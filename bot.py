import asyncio
import random
import discord
from discord import app_commands
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
NGON_FILE = BASE_DIR / "ngon_da_them_hash.txt"

def load_ngon():
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

import os

TOKEN = os.getenv("DISCORD_TOKEN")

loop_tasks: dict[int, list[asyncio.Task]] = {}
ngon_tasks: dict[int, list[asyncio.Task]] = {}

ngon_indexes: dict[int, int] = {}
ngon_queues: dict[int, list[str]] = {}
MIN_INTERVAL = 0.1
TREO_MIN_INTERVAL = 1.0
treo_tasks: dict[int, list[asyncio.Task]] = {}

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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

OWNER_ID = 1417497667449126952  # ID của boss man
ADMIN_IDS = {OWNER_ID}

async def admin_only(interaction: discord.Interaction) -> bool:
    # Boss luôn có quyền
    if interaction.user.id == OWNER_ID:
        return True

    # Những người đã được /add cấp quyền
    if interaction.user.id in ADMIN_IDS:
        return True

@client.event
async def on_ready():
    synced = await tree.sync()   # Sync cho mọi server bot tham gia

    print("=" * 45)
    print(f"🤖 Bot: {client.user}")
    print(f"🆔 ID: {client.user.id}")
    print(f"🌍 Đã tham gia {len(client.guilds)} server")
    print(f"⚡ Đã sync {len(synced)} lệnh toàn cục")
    print("=" * 45)

    for i, guild in enumerate(client.guilds, start=1):
        print(f"{i}. {guild.name} ({guild.id})")

@tree.command(name="add", description="Thêm người dùng làm admin")
@app_commands.describe(user="Người dùng muốn cấp quyền")
async def add(interaction: discord.Interaction, user: discord.User):
    # Chỉ OWNER mới được cấp quyền
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Chỉ boss mới cấp quyền.",
            ephemeral=True,
        )
        return

    if user.id in ADMIN_IDS:
        await interaction.response.send_message(
            f"⚠️ {user.mention} đã là admin.",
            ephemeral=True,
        )
        return

    ADMIN_IDS.add(user.id)

    await interaction.response.send_message(
        f"✅ Đã thêm {user.mention} làm admin.",
        ephemeral=True,
    )
@tree.command(name="listadmin", description="Xem danh sách admin bot")
async def listadmin(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    if not ADMIN_IDS:
        await interaction.response.send_message(
            "📋 Hiện không có admin nào.",
            ephemeral=True,
        )
        return

    lines = []
    for user_id in sorted(ADMIN_IDS):
        user = client.get_user(user_id)
        if user:
            lines.append(f"• {user.mention} ({user.id})")
        else:
            lines.append(f"• User ID: {user_id}")

    await interaction.response.send_message(
        "👑 **Danh sách Admin**\n\n" + "\n".join(lines),
        ephemeral=True,
    )


@tree.command(name="removeadmin", description="Xóa quyền admin của người dùng")
@app_commands.describe(user="Người dùng muốn xóa quyền")
async def removeadmin(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Chỉ boss mới thu quyền.",
            ephemeral=True,
        )
        return

    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Không thể tự xóa quyền của chính mình.",
            ephemeral=True,
        )
        return

    if user.id not in ADMIN_IDS:
        await interaction.response.send_message(
            f"⚠️ {user.mention} không phải admin.",
            ephemeral=True,
        )
        return

    ADMIN_IDS.remove(user.id)

    await interaction.response.send_message(
        f"✅ Đã xóa quyền admin của {user.mention}.",
        ephemeral=True,
    )
    ADMIN_IDS.remove(user.id)

    await interaction.response.send_message(
        f"✅ Đã xóa quyền admin của {user.mention}.",
        ephemeral=True
    )
    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Không thể tự xóa quyền của chính mình.",
            ephemeral=True,
        )
        return

    if user.id not in ADMIN_IDS:
        await interaction.response.send_message(
            f"⚠️ {user.mention} không phải admin.",
            ephemeral=True,
        )
        return

    ADMIN_IDS.remove(user.id)

    await interaction.response.send_message(
        f"✅ Đã xóa quyền admin của {user.mention}.",
        ephemeral=True,
    )
@tree.command(name="servers", description="Xem các server bot đang ở")
async def servers(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Chỉ boss mới xem được.",
            ephemeral=True
        )
        return

    if not client.guilds:
        await interaction.response.send_message(
            "Bot chưa ở server nào.",
            ephemeral=True
        )
        return

    lines = []
    for g in client.guilds:
        lines.append(
            f"**{g.name}**\nID: `{g.id}` | Thành viên: {g.member_count}"
        )

    await interaction.response.send_message(
        "## 🌍 Danh sách server\n\n" + "\n\n".join(lines),
        ephemeral=True
    )
@tree.command(name="startsay", description="Bật gửi tin định kỳ")
@app_commands.describe(
    message="Nội dung muốn gửi",
    seconds="Khoảng cách giữa các lần gửi (tối thiểu 0.1)",
    user="Người dùng muốn tag (không bắt buộc)"
)
async def startsay(
    interaction: discord.Interaction,
    message: str,
    seconds: float,
    user: discord.User | None = None
):
    if not await admin_only(interaction):
        return
    if seconds < MIN_INTERVAL:
        seconds = MIN_INTERVAL
    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message("❌ Không xác định được channel.", ephemeral=True)
        return
    channel_id = interaction.channel_id

    async def sender():
        while True:
            try:
                content = f"{message} {user.mention}" if user else message
                await channel.send(content, allowed_mentions=discord.AllowedMentions(users=True))
                await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                raise
            except discord.HTTPException as e:
                print(f"[DISCORD ERROR] {e}")
                await asyncio.sleep(seconds)

    loop_tasks.setdefault(channel_id, []).append(asyncio.create_task(sender()))
    tag_text = f" và tag {user.mention}" if user else ""
    await interaction.response.send_message(
        f"✅ Đã bật gửi tin mỗi {seconds:g} giây{tag_text}.",
        ephemeral=True,
    )

@tree.command(name="stopsay", description="Tắt tất cả gửi tin định kỳ trong kênh")
async def stopsay(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    channel_id = interaction.channel_id
    tasks_list = loop_tasks.pop(channel_id, None)

    if tasks_list:
        for t in tasks_list:
            t.cancel()
        await interaction.response.send_message(
            "✅ Đã tắt tất cả loop trong channel này.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "ℹ️ Channel này không có loop nào đang chạy.",
            ephemeral=True,
        )

@tree.command(name="startngon", description="Đọc lần lượt các dòng từ file")
@app_commands.describe(
    seconds="Khoảng cách giữa các lần gửi (tối thiểu 0.1)",
    user="Người dùng muốn tag (không bắt buộc)"
)
async def startngon(
    interaction: discord.Interaction,
    seconds: float = MIN_INTERVAL,
    user: discord.User | None = None
):
    if not await admin_only(interaction):
        return

    if seconds < MIN_INTERVAL:
        seconds = MIN_INTERVAL

    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message(
            "❌ Không xác định được channel.",
            ephemeral=True
        )
        return

    channel_id = interaction.channel_id

    if not load_ngon():
        await interaction.response.send_message(
            "❌ File không tồn tại hoặc không có dòng nào.",
            ephemeral=True
        )
        return

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
                    allowed_mentions=discord.AllowedMentions(users=True)
                )
                await asyncio.sleep(seconds)

            except asyncio.CancelledError:
                raise
            except discord.HTTPException as e:
                print(f"[NGON DISCORD ERROR] {e}")
                await asyncio.sleep(max(seconds, MIN_INTERVAL))

    ngon_tasks.setdefault(channel_id, []).append(asyncio.create_task(ngon_sender()))

    tag_text = f" và tag {user.mention}" if user else ""
    await interaction.response.send_message(
        f"✅ Đã bắt đầu đọc file mỗi {seconds:g} giây{tag_text}.",
        ephemeral=True,
    )


@tree.command(name="stopngon", description="Dừng tất cả vòng đọc file trong kênh")
async def stopngon(interaction: discord.Interaction):
    if not await admin_only(interaction):
        return

    channel_id = interaction.channel_id
    tasks_list = ngon_tasks.pop(channel_id, None)

    if tasks_list:
        for t in tasks_list:
            t.cancel()
        await interaction.response.send_message(
            "✅ Đã dừng tất cả vòng đọc file trong channel này.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "ℹ️ Channel này không có vòng đọc file nào.",
            ephemeral=True,
        )


if not TOKEN:
    raise RuntimeError("Chưa đặt biến môi trường DISCORD_TOKEN.")

print("=== TEST FILE NGON ===")
print("Đường dẫn:", NGON_FILE)
print("Tồn tại:", NGON_FILE.exists())
data = load_ngon()
print("Số dòng:", len(data))
print("======================")

@client.event
async def on_error(event, *args, **kwargs):
    import traceback
    print(f"Lỗi ở event: {event}")
    traceback.print_exc()

# =========================
# /starttreo - Tự động gửi 9 dòng
# =========================

@tree.command(name="starttreo", description="Tự động gửi 9 dòng với nội dung và link tùy chỉnh.")
@app_commands.describe(noidung="Nội dung muốn hiển thị", bio="Link muốn gắn", delay="Khoảng cách gửi (giây)")
async def starttreo(interaction: discord.Interaction, noidung: str, bio: str, delay: float):
    if delay < TREO_MIN_INTERVAL: delay = TREO_MIN_INTERVAL
    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message("❌ Không xác định được channel.", ephemeral=True); return
    noidung=noidung.strip(); bio=bio.strip()
    if not bio.startswith(("http://","https://")): bio="https://"+bio
    message="\n".join([f"# > [ {noidung}](<{bio}>)"]*9)
    async def treo_loop():
        while True:
            try:
                await channel.send(message)
                await asyncio.sleep(delay)
            except asyncio.CancelledError: raise
            except discord.HTTPException: await asyncio.sleep(delay)
    treo_tasks.setdefault(interaction.channel_id,[]).append(asyncio.create_task(treo_loop()))
    await interaction.response.send_message(f"✅ Đã bật gửi mỗi {delay:g} giây.", ephemeral=True)

@tree.command(name="stoptreo", description="Dừng toàn bộ vòng gửi trong kênh.")
async def stoptreo(interaction: discord.Interaction):
    tasks=treo_tasks.pop(interaction.channel_id,None)
    if tasks:
        [t.cancel() for t in tasks]
        await interaction.response.send_message("✅ Đã dừng.", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ Không có vòng nào đang chạy.", ephemeral=True)

client.run(TOKEN)