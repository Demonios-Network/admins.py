import html 
import os 
 
from telegram import ParseMode, Update 
from telegram.error import BadRequest 
from telegram.ext import CallbackContext, CommandHandler, Filters 
from telegram.utils.helpers import mention_html 
from telethon import * 
from telethon import events 
from telethon.errors import * 
from telethon.tl import * 
from telethon.tl import functions, types 
 
from NekoRobot import DRAGONS, NEKO_PTB 
from NekoRobot import tbot as bot 
from NekoRobot.modules.disable import DisableAbleCommandHandler 
from NekoRobot.modules.helper_funcs.alternate import send_message 
from NekoRobot.modules.helper_funcs.chat_status import ( 
    ADMIN_CACHE, 
    bot_admin, 
    can_pin, 
    can_promote, 
    connection_status, 
    user_admin, 
    user_can_changeinfo, 
    user_can_pin, 
) 
from NekoRobot.modules.helper_funcs.extraction import ( 
    extract_user, 
    extract_user_and_text, 
) 
from NekoRobot.modules.log_channel import loggable 
 
 
async def is_register_admin(chat, user): 
    if isinstance(chat, (types.InputPeerChannel, types.InputChannel)): 
        return isinstance( 
            ( 
                await bot(functions.channels.GetParticipantRequest(chat, user)) 
            ).participant, 
            (types.ChannelParticipantAdmin, types.ChannelParticipantCreator), 
        ) 
    if isinstance(chat, types.InputPeerUser): 
        return True 
 
 
async def can_promote_users(message): 
    result = await bot( 
        functions.channels.GetParticipantRequest( 
            channel=message.chat_id, 
            user_id=message.sender_id, 
        ) 
    ) 
    p = result.participant 
    return isinstance(p, types.ChannelParticipantCreator) or ( 
        isinstance(p, types.ChannelParticipantAdmin) and p.admin_rights.ban_users 
    ) 
 
 
async def can_ban_users(message): 
    result = await bot( 
        functions.channels.GetParticipantRequest( 
            channel=message.chat_id, 
            user_id=message.sender_id, 
        ) 
    ) 
    p = result.participant 
    return isinstance(p, types.ChannelParticipantCreator) or ( 
        isinstance(p, types.ChannelParticipantAdmin) and p.admin_rights.ban_users 
    ) 
 
 
@bot.on(events.NewMessage(pattern="/users$")) 
async def get_users(show): 
    if not show.is_group:
      return
    user = await get_user_from_event(dmod)
    if not dmod.is_group:
        return

    if not await is_register_admin(dmod.input_chat, user.id):
        await dmod.reply("Darling, i cant demote non-admin")
        return
    if not user:
        return

    # New rights after demotion
    newrights = ChatAdminRights(
        add_admins=False,
        invite_users=True,
        change_info=False,
        ban_users=False,
        delete_messages=True,
        pin_messages=False,
    )
    # Edit Admin Permission
    try:
        await bot(EditAdminRequest(dmod.chat_id, user.id, newrights, "Admin"))
        await dmod.reply("Demoted Successfully!")

    # If we catch BadRequestError from Telethon
    # Assume we don't have permission to demote
    except Exception:
        await dmod.reply("Failed to demote.")
        return


@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def demote(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "You don't seem to be referring to a user or the ID specified is incorrect..",
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status == "creator":
        message.reply_text("This person CREATED the chat, how would I demote them?")
        return

    if user_member.status != "administrator":
        message.reply_text("Can't demote what wasn't promoted!")
        return

    if user_id == bot.id:
        message.reply_text("I can't demote myself! Get an admin to do it for me.")
        return

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_voice_chats=False,
        )
        message.reply_text(
            f"Successfully demoted <b>{user_member.user.first_name or user_id}</b>!",
            parse_mode=ParseMode.HTML,
        )

        return f"<b>{html.escape(chat.title)}:</b>\n#DEMOTED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"

    except BadRequest:
        message.reply_text(
            "Could not demote. I might not be admin, or the admin status was appointed by another"
            " user, so I can't act upon them!",
        )
        return


@user_admin
def refresh_admin(update, _):
    try:
        ADMIN_CACHE.pop(update.effective_chat.id)
    except (KeyError, IndexError):
        pass

    update.effective_message.reply_text("Admins cache refreshed!")


@connection_status
@bot_admin
@can_promote
@user_admin
def set_title(update: Update, context: CallbackContext):
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message

    user_id, title = extract_user_and_text(message, args)
    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if not user_id:
        message.reply_text(
            "You don't seem to be referring to a user or the ID specified is incorrect..",
)
        return

    if user_member.status == "creator":
        message.reply_text(
            "This person CREATED the chat, how can i set custom title for him?",
        )
        return

    if user_member.status != "administrator":
        message.reply_text(
            "Can't set title for non-admins!\nPromote them first to set custom title!",
        )
        return

    if user_id == bot.id:
        message.reply_text(
            "I can't set my own title myself! Get the one who made me admin to do it for me.",
        )
        return

    if not title:
        message.reply_text("Setting blank title doesn't do anything!")
        return

    if len(title) > 16:
        message.reply_text(
            "The title length is longer than 16 characters.\nTruncating it to 16 characters.",
        )

    try:
        bot.setChatAdministratorCustomTitle(chat.id, user_id, title)
    except BadRequest:
        message.reply_text(
            "Either they aren't promoted by me or you set a title text that is impossible to set."
        )
        return

    bot.sendMessage(
        chat.id,
        f"Sucessfully set title for <code>{user_member.user.first_name or user_id}</code> "
        f"to <code>{html.escape(title[:16])}</code>!",
        parse_mode=ParseMode.HTML,
    )


@bot_admin
@can_pin
@user_admin
@loggable
def pin(update, context):
    bot, args = context.bot, context.args
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    is_group = chat.type not in ["private", "channel"]

    prev_message = update.effective_message.reply_to_message

    if user_can_pin(chat, user, bot.id) is False:
        message.reply_text("You are missing rights to pin a message!")
        return ""

    if not prev_message:
        message.reply_text("Reply to the message you want to pin!")
        return

    if is_group:
        is_silent = (
            (
                args[0].lower() != "notify"
                or args[0].lower() == "loud"
                or args[0].lower() == "violent"
            )
            if len(args) >= 1
            else True
        )

        try:
            bot.pinChatMessage(
                chat.id, prev_message.message_id, disable_notification=is_silent
            )
        except BadRequest as excp:
            if excp.message != "Chat_not_modified":
                raise
        return f"<b>{html.escape(chat.title)}:</b>\n#PINNED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}"

    return ""


@bot_admin
@can_pin
@user_admin
@loggable
def unpin(update, context):
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user_can_pin(chat, user, bot.id) is False:
        message.reply_text("You are missing rights to unpin a message!")
        return ""

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        elif excp.message == "Message to unpin not found":
            message.reply_text(
                "I can't see pinned message, Maybe already unpinned, or pin message to old!"
            )
        else:
            raise

    return f"<b>{html.escape(chat.title)}:</b>\n#UNPINNED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}"


@bot_admin
def pinned(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    msg = update.effective_message
    msg_id = (
        update.effective_message.reply_to_message.message_id
        if update.effective_message.reply_to_message
        else update.effective_message.message_id
)

    chat = bot.getChat(chat_id=msg.chat.id)
    if chat.pinned_message:
        pinned_id = chat.pinned_message.message_id
        if msg.chat.username:
            link_chat_id = msg.chat.username
            message_link = f"https://t.me/{link_chat_id}/{pinned_id}"
        elif (str(msg.chat.id)).startswith("-100"):
            link_chat_id = (str(msg.chat.id)).replace("-100", "")
            message_link = f"https://t.me/c/{link_chat_id}/{pinned_id}"

        msg.reply_text(
            f'The pinned message of {html.escape(chat.title)} is <a href="{message_link}">here</a>.',
            reply_to_message_id=msg_id,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    else:
        msg.reply_text(f"There is no pinned message in {html.escape(chat.title)}!")


@bot_admin
@user_admin
@connection_status
def invite(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat

    if chat.username:
        update.effective_message.reply_text(f"https://t.me/{chat.username}")
    elif chat.type in [chat.SUPERGROUP, chat.CHANNEL]:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text(
                "I don't have access to the invite link, try changing my permissions!",
            )
    else:
        update.effective_message.reply_text(
            "I can only give you invite links for supergroups and channels, sorry!",
        )


@connection_status
def adminlist(update, context):
    chat = update.effective_chat  # type: Optional[Chat] -> unused variable
    user = update.effective_user  # type: Optional[User]
    args = context.args  # -> unused variable
    bot = context.bot

    if update.effective_message.chat.type == "private":
        send_message(update.effective_message, "This command only works in Groups.")
        return

    update.effective_chat
    chat_id = update.effective_chat.id
    chat_name = update.effective_message.chat.title  # -> unused variable

    try:
        msg = update.effective_message.reply_text(
            "Fetching group admins...",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        msg = update.effective_message.reply_text(
            "Fetching group admins...",
            quote=False,
            parse_mode=ParseMode.HTML,
        )

    administrators = bot.getChatAdministrators(chat_id)
    text = f"Admins in <b>{html.escape(update.effective_chat.title)}</b>:"

    for admin in administrators:
        user = admin.user
        status = admin.status
        custom_title = admin.custom_title

        if user.first_name == "":
            name = "☠ Deleted Account"
        else:
            name = "{}".format(
                mention_html(
                    user.id,
                    html.escape(f"{user.first_name} " + ((user.last_name or ""))),
                )
            )

        if user.is_bot:
            administrators.remove(admin)
            continue

        # if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "creator":
            text += "\n 🌏 Creator:"
            text += f"\n<code> • </code>{name}\n"

            if custom_title:
                text += f"<code> ┗━ {html.escape(custom_title)}</code>\n"

    text += "\n🌟 Admins:"

    custom_admin_list = {}
    normal_admin_list = []

    for admin in administrators:
        user = admin.user
        status = admin.status
        custom_title = admin.custom_title
• /setsticker*:* Set group sticker
"""

SET_DESC_HANDLER = CommandHandler(
    "setdesc", set_desc, filters=Filters.chat_type.groups, run_async=True
)
SET_STICKER_HANDLER = CommandHandler(
    "setsticker", set_sticker, filters=Filters.chat_type.groups, run_async=True
)
SETCHATPIC_HANDLER = CommandHandler(
    "setgpic", setchatpic, filters=Filters.chat_type.groups, run_async=True
)
RMCHATPIC_HANDLER = CommandHandler(
    "delgpic", rmchatpic, filters=Filters.chat_type.groups, run_async=True
)
SETCHAT_TITLE_HANDLER = CommandHandler(
    "setgtitle", setchat_title, filters=Filters.chat_type.groups, run_async=True
)

ADMINLIST_HANDLER = DisableAbleCommandHandler(
    ["admins", "adminlist"], adminlist, run_async=True
)

PIN_HANDLER = CommandHandler(
    "pin", pin, filters=Filters.chat_type.groups, run_async=True
)
UNPIN_HANDLER = CommandHandler(
    "unpin", unpin, filters=Filters.chat_type.groups, run_async=True
)
PINNED_HANDLER = CommandHandler(
    "pinned", pinned, filters=Filters.chat_type.groups, run_async=True
)

INVITE_HANDLER = DisableAbleCommandHandler("invitelink", invite, run_async=True)

PROMOTE_HANDLER = DisableAbleCommandHandler("promote", promote, run_async=True)
FULLPROMOTE_HANDLER = DisableAbleCommandHandler(
    "fullpromote", fullpromote, run_async=True
)
LOW_PROMOTE_HANDLER = DisableAbleCommandHandler(
    "lowpromote", lowpromote, run_async=True
)
MID_PROMOTE_HANDLER = DisableAbleCommandHandler(
    "midpromote", midpromote, run_async=True
)
DEMOTE_HANDLER = DisableAbleCommandHandler("demote", demote, run_async=True)

SET_TITLE_HANDLER = CommandHandler("title", set_title, run_async=True)
ADMIN_REFRESH_HANDLER = CommandHandler(
    "admincache", refresh_admin, filters=Filters.chat_type.groups, run_async=True
)

Nezuko_PTB.add_handler(SET_DESC_HANDLER)
Nezuko_PTB.add_handler(SET_STICKER_HANDLER)
Nezuko_PTB.add_handler(SETCHATPIC_HANDLER)
Nezuko_PTB.add_handler(RMCHATPIC_HANDLER)
Nezuko_PTB.add_handler(SETCHAT_TITLE_HANDLER)
Nezuko_PTB.add_handler(ADMINLIST_HANDLER)
Nezuko_PTB.add_handler(PIN_HANDLER)
Nezuko_PTB.add_handler(UNPIN_HANDLER)
Nezuko_PTB.add_handler(PINNED_HANDLER)
Nezuko_PTB.add_handler(INVITE_HANDLER)
Nezuko_PTB.add_handler(PROMOTE_HANDLER)
Nezuko_PTB.add_handler(FULLPROMOTE_HANDLER)
Nezuko_PTB.add_handler(LOW_PROMOTE_HANDLER)
Nezuko_PTB.add_handler(MID_PROMOTE_HANDLER)
Nezuko_PTB.add_handler(DEMOTNezuko_HANDLER)
nezuko_PTB.add_handler(SET_TITLE_HANDLER)
Nezuko_PTB.add_handler(ADMINezuko_REFRESH_HANDLER)

mod_name = "Admins"
command_list = [
    "setdesc" "setsticker" "setgpic" "delgpic" "setgtitle" "adminlist",
    "admins",
    "invitelink",
    "promote",
    "fullpromote",
    "lowpromote",
    "midpromote",
    "demote",
    "admincache",
]
handlers = [
    SET_DESC_HANDLER,
    SET_STICKER_HANDLER,
    SETCHATPIC_HANDLER,
    RMCHATPIC_HANDLER,
    SETCHAT_TITLE_HANDLER,
    ADMINLIST_HANDLER,
    PIN_HANDLER,
    UNPIN_HANDLER,
    PINNED_HANDLER,
    INVITE_HANDLER,
    PROMOTE_HANDLER,
    FULLPROMOTE_HANDLER,
    LOW_PROMOTE_HANDER,
    MID_PROMOTE_HANDLER,
    DEMOTE_HANDLER,
    SET_TITLE_HANDLER,
    ADMIN_REFRESH_HANDLER,
]
