import json
import re
import nonebot
import aiohttp, asyncio
import time, datetime
from collections import Counter
from pathlib import Path

from nonebot import require, on_command, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.typing import T_State
from nonebot.params import CommandArg
from nonebot.exception import FinishedException

require("nonebot_plugin_htmlrender")

from nonebot_plugin_htmlrender import (
    md_to_pic,
    get_new_page
)

from playwright.async_api import TimeoutError

from .data import DATA
from .data_medal import DATA_MEDAL

from nonebot.plugin import PluginMetadata


help_text = f"""
插件功能：（tip：命令如果有英文的，大小写都可以支持）
/查 昵称关键词或uid(uid需要以:或：或uid:或UID:或uid：打头)
/查直播 昵称关键词或uid 场次数（默认不写为全部）
/查舰团 昵称关键词或uid
/查昵称 昵称关键词或uid
/查收益 昵称关键词或uid 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)
/查观看 昵称关键词或uid
/查观看2 昵称关键词或uid
/查弹幕 查询的目标人昵称关键词或uid 查询的主播昵称关键词或uid 页数 条数
/查弹幕2 查询的目标人昵称关键词或uid 页数 条数
/查牌子 主播牌子关键词
/查人气 昵称关键词或uid
/查装扮 昵称关键词或uid
/营收 日/周/月榜 人数（不填默认100）
/涨粉 日/周/月榜 人数（不填默认100）
/DD风云榜 人数（不填默认10）
/v详情 昵称关键词或uid
/v直播势
/v急上升
/v急下降
/v舰团
/vdd
/v宏观
/dmk查用户 昵称关键词或uid
/dmk查直播 昵称关键词或uid
/blg查弹幕 昵称关键词或uid
/blg查入场 昵称关键词或uid
/blg查礼物 昵称关键词或uid
/blg直播记录 昵称关键词或uid
/blg直播间sc 昵称关键词或uid
/icu查直播 昵称关键词或uid
/icu查直播 昵称关键词或uid
/lap查用户 昵称关键词或uid
/lap查牌子 昵称关键词或uid
/lap查充电 昵称关键词或uid
/lapdd排行榜 搜索类型(默认0: 月供，1: 总督，2: 提督，3：舰长)
/斗虫 主播1的昵称关键词或uid 主播2的昵称关键词或uid 主播n的昵称关键词或uid（主播数得至少2个） 日期起始偏移值(就是以今天开始前推n天，例如:2，就是前天) 日期结束偏移值
/vtb网站 或 /vtb资源
/eh查直播 或 /诶嘿查直播


调用的相关API源自b站官方接口、danmakus.com、ddstats.ericlamm.xyz、biligank.com、laplace.live、vtbs.fun、stats.nailv.live
""".strip()

__plugin_meta__ = PluginMetadata(
    name = 'b站用户信息查询',
    description = '适用于nonebot2 v11的b站用户信息查询插件【粉丝、舰团信息；直播收益数据；直播观看信息；关键词搜昵称、UID等；主播营收榜单】',
    usage = help_text
)

# 请求头 需要在env配置cookie
header1 = {
    'content-type': 'text/plain; charset=utf-8',
    'cookie': '',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Core/1.94.186.400 QQBrowser/11.3.5195.400'
}

# 获取env配置
try:
    nonebot.logger.debug(nonebot.get_driver().config.searchbiliinfo_cookie)
    header1["cookie"] = nonebot.get_driver().config.searchbiliinfo_cookie
except:
    header1["cookie"] = ""
    nonebot.logger.warning("searchBiliInfo的cookie没有配置，部分功能受限。")

nonebot.logger.debug("cookie=" + header1["cookie"])

# 所有的命令都在这哦，要改命令触发关键词的请自便
catch_str = on_command("查", priority=2)
catch_str1 = on_command("查弹幕")
catch_str11 = on_command("查弹幕2")
catch_str2 = on_command("查观看")
catch_str26 = on_command("查观看2")
catch_str3 = on_command("查直播")
catch_str4 = on_command('查收益')
catch_str5 = on_command('查舰团')
catch_str6 = on_command('查昵称')
catch_str12 = on_command('查牌子')
catch_str22 = on_command('查人气')
catch_str35 = on_command('查装扮', aliases={"查装扮"})
catch_str7 = on_command('营收')
catch_str9 = on_command('涨粉')
catch_str8 = on_command("vtb网站", aliases={"VTB网站", "Vtb网站", "vtb资源", "VTB资源"})
catch_str10 = on_command('DD风云榜', aliases={"风云榜", "dd风云榜"})
catch_str13 = on_command('V详情', aliases={"v详情", "v详细", "V详细"})
catch_str29 = on_command('V直播势', aliases={"v直播势"})
catch_str30 = on_command('V急上升', aliases={"v急上升"})
catch_str31 = on_command('V急下降', aliases={"v急下降"})
catch_str32 = on_command('V舰团', aliases={"v舰团"})
catch_str33 = on_command('VDD风云榜', aliases={"vdd风云榜", "vdd", "VDD"})
catch_str34 = on_command('V宏观', aliases={"v宏观"})
catch_str14 = on_command('dmk查用户', aliases={"DMK查用户", "danmakus查用户"})
catch_str15 = on_command('dmk查直播', aliases={"DMK查直播", "danmakus查直播"})
catch_str16 = on_command('blg查弹幕', aliases={"BLG查弹幕", "biligank查弹幕"})
catch_str17 = on_command('blg查入场', aliases={"BLG查入场", "biligank查入场"})
catch_str18 = on_command('blg查礼物', aliases={"BLG查礼物", "biligank查礼物"})
catch_str19 = on_command('blg直播记录', aliases={"BLG直播记录", "biligank直播记录"})
catch_str20 = on_command('blg直播间sc', aliases={"BLG直播间sc", "blg直播间SC", "BLG直播间SC", "biligank直播间sc"})
catch_str21 = on_command('icu查直播', aliases={"ICU查直播", "matsuri查直播"})
catch_str23 = on_command('lap查用户', aliases={"LAP查用户"})
catch_str24 = on_command('lap查牌子', aliases={"LAP查牌子"})
catch_str27 = on_command('lap查充电', aliases={"LAP查充电"})
catch_str36 = on_command('lapdd排行榜', aliases={"lapdd", "LAPDD排行榜", "LAPDD"})
catch_str25 = on_command('zero查用户', aliases={"ZERO查用户"})
catch_str28 = on_command('zero被关注', aliases={"ZERO被关注"})
#catch_str37 = on_regex(r"(?P<option>斗虫|主播pk|主播PK) (?P<usernames>(?:[\u4e00-\u9fa5\w\d]{1,30} ){1,})(?:#(?P<start_offset>\d*) (?P<end_offset>\d*))?")
#catch_str37 = on_regex(r"(?P<option>斗虫|主播pk|主播PK) (?P<usernames>(?:[\u4e00-\u9fa5\w\d]{1,30} ){1,})(?:#(?P<start_offset>\d*) (?P<end_offset>\d*))?")
catch_str37 = on_regex(r"(?P<option>斗虫|主播pk|主播PK) (?P<usernames>(?:[\u4e00-\u9fa5\w\d]{1,30}(?: )?){1,})(?:#(?P<start_offset>\d*) (?P<end_offset>\d*))?")
catch_str38 = on_command('eh查直播', aliases={"诶嘿查直播", "eihei查直播"})

# 查
@catch_str.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到用户名为：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), reply_message=True)

    # 传入uid获取用户基本信息
    url = 'https://account.bilibili.com/api/member/getCardByMid?mid=' + content
    base_info_json = await common_get_return_json(url)

    if base_info_json == None:
        msg = '查询UID：' + content + '的用户信息失败，可能是网络问题或者API寄了喵'
        await catch_str.finish(Message(f'{msg}'), reply_message=True)

    # 获取用户信息失败
    if base_info_json['code'] != 0:
        nonebot.logger.info(base_info_json)
        msg = '获取uid：' + content + '，用户信息失败。\nError code：' + str(base_info_json['code'])
        await catch_str.finish(Message(f'{msg}'), reply_message=True)

    # 获取用户直播间id
    room_id = await get_room_id(content)
    # 没有直播间 默认为0
    if room_id == 0:
        guard_info_json = {"data": {"info": {"num": 0}}}
    else:
        url = 'https://api.live.bilibili.com/xlive/app-room/v2/guardTab/topList?roomid=' + str(room_id) + \
            '&page=1&ruid=' + content + '&page_size=0'
        guard_info_json = await common_get_return_json(url)

    if guard_info_json == None:
        msg = "请求失败喵~可能是网络问题或者API寄了喵~"
        await catch_str.finish(Message(f'{msg}'), reply_message=True)

    try:
        msg = '用户名：' + base_info_json['card']['name'] + '\nUID：' + str(base_info_json['card']['mid']) + \
            '\n房间号：' + str(room_id) + '\n粉丝数：' + str(base_info_json['card']['fans']) + '\n舰团数：' + str(
            guard_info_json['data']['info']['num'])
    except:
        msg = "数据解析异常，请重试。（如果多次重试都失败，建议提issue待开发者修复）"
    await catch_str.finish(Message(f'{msg}'), reply_message=True)


# 查弹幕
@catch_str1.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid 目标uid 页数 条数
    content = content.split()
    src_uid = ""
    tgt_uid = ""
    page = "0"
    page_size = "3"

    if len(content) >= 2:
        src_uid, tgt_uid, *args = content
        page = args[0] if args else "0"
        page_size = args[1] if len(args) > 1 else "3"
    else:
        msg = '传参错误，命令格式【/查弹幕 用户uid或昵称 目标uid或昵称 页数(可不填，默认0) 条数(可不填，默认3)】'
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        msg = '查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        nonebot.logger.info(temp)
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)
    
    temp = await data_preprocess(tgt_uid)
    if 0 == temp["code"]:
        tgt_uid = temp["uid"]
    else:
        msg = '查询不到用户名为：' + tgt_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        nonebot.logger.info(temp)
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)

    nonebot.logger.debug("src_uid:" + src_uid + " tgt_uid:" + tgt_uid)

    await catch_str1.send("正在获取数据中，请耐心等待...", reply_message=True)

    url = 'https://danmakus.com/api/search/user/detail?uid=' + src_uid + '&target=' + tgt_uid + \
            '&pagenum=' + page + '&pagesize=' + page_size
    info_json = await common_get_return_json(url)

    if info_json == None:
        msg = '果咩，查询信息失败喵~API寄了喵'
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '查询出错。Error code：' + str(temp["code"])
            nonebot.logger.info(info_json)

            await catch_str1.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        msg = '果咩，查询信息失败喵~请检查拼写或者是API寄了'
        nonebot.logger.info(e)
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)

    data_len = 0
    out_str = "#查弹幕\n\n查询用户UID:" + src_uid + \
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;目标UID:" + tgt_uid + \
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;页数:" + page + \
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;条数:" + page_size + "\n\n" + \
        "| 时间 | 内容 |\n" \
        "| :-----| :-----|\n"

    try:
        for i in range(len(info_json['data']['data'])):
            title = await filter_markdown(info_json['data']['data'][i]['live']['title'])
            out_str += '| 标题 | ' + title + ' |\n'
            for j in range(len(info_json['data']['data'][i]['danmakus'])):
                date = await timestamp_to_date(info_json['data']['data'][i]['danmakus'][j]['sendDate'])
                if info_json['data']['data'][i]['danmakus'][j]['type'] in [0, 1, 2, 3]:
                    message = await filter_markdown(info_json['data']['data'][i]['danmakus'][j]['message'])
                elif info_json['data']['data'][i]['danmakus'][j]['type'] == 4:
                    message = "【进入直播间】"
                else:
                    message = "【其他消息】"
                out_str += '| ' + str(date) + '| ' + message + '|\n'
                data_len += 1
            out_str += '| -- | -- |\n'
        out_str += '\n数据源自：danmakus.com\n'
    # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '返回数据解析异常，寄~（请查日志排查问题）'
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)

    # 随便定的一个上限值 可以自行修改
    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str1.send(MessageSegment.image(output))
    else:
        msg = '果咩，弹幕数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str1.finish(Message(f'{msg}'), reply_message=True)


# 查弹幕2
@catch_str11.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid 页数 条数
    content = content.split()
    src_uid = ""
    tgt_uid = ""
    page = "0"
    page_size = "3"

    if content:
        src_uid, *args = content
        page = args[0] if args else "0"
        page_size = args[1] if len(args) > 1 else "3"
    else:
        msg = '传参错误，命令格式【/查弹幕2 用户uid或昵称 页数(可不填，默认0) 条数(可不填，默认3)】'
        await catch_str11.finish(Message(f'{msg}'), reply_message=True)
 
    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str11.finish(Message(f'{msg}'), reply_message=True)

    nonebot.logger.debug("src_uid:" + src_uid + " tgt_uid:" + tgt_uid)

    await catch_str11.send("正在获取数据中，请耐心等待...", reply_message=True)

    url = 'https://danmakus.com/api/search/user/detail?uid=' + src_uid + '&target=' + tgt_uid + \
            '&pagenum=' + page + '&pagesize=' + page_size
    info_json = await common_get_return_json(url)

    if info_json == None:
        msg = '果咩，查询信息失败喵~API寄了喵'
        await catch_str11.finish(Message(f'{msg}'), reply_message=True)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '查询出错。接口返回：\n' + json.dumps(info_json, indent=2, ensure_ascii=False)
            await catch_str11.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '果咩，查询信息失败喵~请检查拼写或者是API寄了'
        await catch_str11.finish(Message(f'{msg}'), reply_message=True)

    data_len = 0
    out_str = "#查弹幕2\n\n查询用户UID:" + src_uid + \
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;目标UID:" + tgt_uid + \
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;页数:" + page + \
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;条数:" + page_size + "\n\n" + \
        "| 时间 | 内容 |\n" \
        "| :-----| :-----|\n"

    try:
        for i in range(len(info_json['data']['data'])):
            name = info_json['data']['data'][i]['channel']['name']
            title = await filter_markdown(info_json['data']['data'][i]['live']['title'])
            out_str += '| 主播——标题 | ' + name + '——' + title + ' |\n'
            for j in range(len(info_json['data']['data'][i]['danmakus'])):
                date = await timestamp_to_date(info_json['data']['data'][i]['danmakus'][j]['sendDate'])
                if info_json['data']['data'][i]['danmakus'][j]['type'] in [0, 1, 2, 3]:
                    message = await filter_markdown(info_json['data']['data'][i]['danmakus'][j]['message'])
                elif info_json['data']['data'][i]['danmakus'][j]['type'] == 4:
                    message = "【进入直播间】"
                else:
                    message = "【其他消息】"
                out_str += '| ' + str(date) + '| ' + message + '|\n'
                data_len += 1
            out_str += '| -- | -- |\n'
        out_str += '\n数据源自：danmakus.com\n'
    # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '返回数据解析异常，寄~（请查日志排查问题）'
        await catch_str11.finish(Message(f'{msg}'), reply_message=True)

    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str11.send(MessageSegment.image(output))
    else:
        msg = '果咩，弹幕数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str11.finish(Message(f'{msg}'), reply_message=True)


# 查观看
@catch_str2.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到用户名为：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), reply_message=True)

    await catch_str.send("正在获取数据中，请耐心等待...", reply_message=True)

    url = 'https://danmakus.com/api/search/user/channel?uid=' + content
    user_info_json = await common_get_return_json(url)

    if user_info_json == None:
        msg = '果咩，查询用户信息失败喵~API寄了喵'
        await catch_str2.finish(Message(f'{msg}'), reply_message=True)

    try:
        # 判断返回代码
        if user_info_json['code'] != 200:
            msg = '查询用户：' + content + '失败'
            await catch_str2.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '果咩，查询用户信息失败喵~请检查拼写或者是API寄了'
        await catch_str2.finish(Message(f'{msg}'), reply_message=True)

    # 创建一个计数器对象，并对重复的uId进行计数
    uid_counter = Counter([(item['uId'], item['name'], item['roomId']) for item in user_info_json['data']])

    # 统计不重复的总数
    unique_uids = set([item['uId'] for item in user_info_json['data']])

    out_str = "#查观看\n\n查询用户UID：" + content + "\n\n" + \
        " 观看总数：" + str(len(user_info_json["data"])) + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;主播总数：" + str(len(unique_uids)) + "\n\n" + \
        "| 昵称 | UID | 房间号 | 观看次数 |\n" \
        "| :-----| :-----| :-----| :-----|\n"

    # nonebot.logger.info(out_str)

    # 按照降序输出计数器对象的结果
    for (uId, name, roomId), count in uid_counter.most_common():
        out_str += "| {:<s} | {:<d} | {:<d} | {:<d} |".format(name, uId, roomId, count)
        out_str += '\n'

    out_str += '\n数据源自：danmakus.com\n'
    # nonebot.logger.info("\n" + out_str)

    if len(unique_uids) < 2000:
        output = await md_to_pic(md=out_str, width=700)
        await catch_str2.send(MessageSegment.image(output))
    else:
        msg = '果咩，dd数大于2000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str2.finish(Message(f'{msg}'), reply_message=True)


# 查观看2
@catch_str26.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str26.finish(Message(f'{msg}'), reply_message=True)

    await catch_str26.send("正在获取数据中，请耐心等待...", reply_message=True)

    
    url = 'https://danmakus.com/api/search/user/channel?uid=' + content
    user_info_json = await common_get_return_json(url)

    if user_info_json == None:
        msg = '果咩，查询用户信息失败喵~API寄了喵'
        await catch_str26.finish(Message(f'{msg}'), reply_message=True)

    try:
        # 判断返回代码
        if user_info_json['code'] != 200:
            msg = '查询用户：' + content + '失败'
            await catch_str26.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '果咩，查询用户信息失败喵~请检查拼写或者是API寄了'
        await catch_str26.finish(Message(f'{msg}'), reply_message=True)

    try:
        dir_path = Path(__file__).parent
        file_path = dir_path / "html" / "composition_page.html"

        async with get_new_page(viewport={"width": 1000, "height": 800}) as page:
            await page.goto(
                "file://" + str(file_path.resolve()),
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            await page.eval_on_selector('html', "generate_chart4('{}', '{}')".format(content, json.dumps(user_info_json)))
            await asyncio.sleep(3)
            temp_path = "./data/danmakus.com_composition" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str26.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str26.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str26.finish(Message(f'{msg}'), reply_message=True)


# 查直播
@catch_str3.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid或昵称 最近n场
    content = content.split()
    src_uid = ""
    info_size = "99999"

    if len(content) < 1 or len(content) > 3 or content[0] == "":
        msg = '传参错误，命令格式【/查直播 用户uid或昵称 最近场次数】'
        await catch_str3.finish(Message(f'{msg}'), reply_message=True)
    else:
        src_uid = content[0]
        if len(content) > 1 and content[1]:
            info_size = content[1]

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str3.finish(Message(f'{msg}'), reply_message=True)

    await catch_str3.send("正在获取数据中，请耐心等待...", reply_message=True)

    url = 'https://danmakus.com/api/info/channel?cid=' + src_uid
    info_json = await common_get_return_json(url)

    if info_json == None:
        msg = '查询用户：' + src_uid + '失败，API寄了喵'
        await catch_str3.finish(Message(f'{msg}'), reply_message=True)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '查询用户：' + src_uid + '失败，请检查拼写或者是API寄了\nError code：' + str(info_json["code"])
            await catch_str3.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询用户：' + src_uid + '失败，请检查拼写或者是API寄了'
        await catch_str3.finish(Message(f'{msg}'), reply_message=True)

    out_str = ""
    try:
        out_str = "#查直播\n\n昵称:" + info_json["data"]["channel"]["name"] + \
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UID:" + src_uid + \
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;房间号:" + str(info_json["data"]["channel"]["roomId"]) +\
                "\n\n 总直播数:" + str(info_json["data"]["channel"]["totalLiveCount"]) + \
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总弹幕数:" + str(info_json["data"]["channel"]["totalDanmakuCount"]) + \
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总收益:￥" + str(info_json["data"]["channel"]["totalIncome"]) + \
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总直播时长:" + str(round(info_json["data"]["channel"]["totalLiveSecond"] / 60 / 60, 2)) + "h\n\n" + \
                "| 开始时间 | 时长 | 标题 | 弹幕数 | 观看数 | 互动数 | 总收益 |\n" \
                "| :-----| :-----| :-----| :-----| :-----| :-----| :-----|\n"
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '解析数据异常（请查日志排查问题）'
        await catch_str3.finish(Message(f'{msg}'), reply_message=True)

    for i in range(len(info_json["data"]["lives"])):
        # 达到指定数量场次
        if i == int(info_size):
            break
        try:
            if info_json["data"]["lives"][i]["stopDate"] is None:
                out_str += "| {:<s} | 直播中 | {:<s} | {:<d} | {:<d} | {:<d} | ￥{:<.1f} |".format(
                    await timestamp_to_date(info_json["data"]["lives"][i]["startDate"]),
                    info_json["data"]["lives"][i]["title"],
                    info_json["data"]["lives"][i]["danmakusCount"],
                    info_json["data"]["lives"][i]["watchCount"],
                    info_json["data"]["lives"][i]["interactionCount"],
                    info_json["data"]["lives"][i]["totalIncome"])
            else:
                out_str += "| {:<s} | {:<.2f}h | {:<s} | {:<d} | {:<d} | {:<d} | ￥{:<.1f} |".format(
                    await timestamp_to_date(info_json["data"]["lives"][i]["startDate"]),
                    (info_json["data"]["lives"][i]["stopDate"] - info_json["data"]["lives"][i][
                        "startDate"]) / 1000 / 3600,
                    info_json["data"]["lives"][i]["title"],
                    info_json["data"]["lives"][i]["danmakusCount"],
                    info_json["data"]["lives"][i]["watchCount"],
                    info_json["data"]["lives"][i]["interactionCount"],
                    info_json["data"]["lives"][i]["totalIncome"])
        except (KeyError, TypeError, IndexError) as e:
            out_str += "| {:<s} | 直播中 | {:<s} | {:<d} | {:<d} | {:<d} | ￥{:<.1f} |".format(
                await timestamp_to_date(info_json["data"]["lives"][i]["startDate"]),
                info_json["data"]["lives"][i]["title"],
                info_json["data"]["lives"][i]["danmakusCount"],
                info_json["data"]["lives"][i]["watchCount"],
                info_json["data"]["lives"][i]["interactionCount"],
                info_json["data"]["lives"][i]["totalIncome"])
        out_str += '\n'
        # 2000场就算了吧，太多了
        if i >= 2000:
            break
    out_str += '\n数据源自：danmakus.com\n'
    # nonebot.logger.info("\n" + out_str)

    if len(info_json["data"]["lives"]) < 2000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str3.send(MessageSegment.image(output))
    else:
        msg = '果咩，直播数大于2000，发不出去喵~'
        await catch_str3.finish(Message(f'{msg}'), reply_message=True)


# 查收益
@catch_str4.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid或昵称 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)
    content = content.split()
    src_uid = ""
    live_index = "0"
    income_type = "1"

    if len(content) < 1 or len(content) > 3 or content[0] == "":
        msg = '传参错误，命令格式【/查直播 用户uid或昵称 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)】'
        await catch_str4.finish(Message(f'{msg}'), reply_message=True)
    else:
        src_uid = content[0]
        if len(content) > 1 and content[1]:
            income_type = content[1]
        if len(content) > 2 and content[2]:
            live_index = content[2]

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), reply_message=True)

    # 默认1: 礼物，2: 上舰或舰长，3: SC
    # 定义了一个名为INCOME_TYPES的字典，其中包含了每种类型收入对应的代码。
    INCOME_TYPES = {
        "礼物": "1",
        "上舰": "2",
        "舰长": "2",
        "SC": "3",
        "sc": "3",
        "Sc": "3",
        "1": "1",
        "2": "2",
        "3": "3"
    }
    # 使用get()方法来获取字典中对应的值，如果找不到则返回默认值"1"
    income_type = INCOME_TYPES.get(income_type, "1")
    # nonebot.logger.info("income_type:" + income_type)

    INCOME_TYPE_CHS = {
        "1": "礼物",
        "2": "上舰",
        "3": "舰长",
    }

    income_type_ch = INCOME_TYPE_CHS.get(income_type, "礼物")

    await catch_str4.send("正在获取数据中，请耐心等待...", reply_message=True)

    url = 'https://danmakus.com/api/info/channel?cid=' + src_uid
    live_json = await common_get_return_json(url)

    try:
        # 判断返回代码
        if live_json['code'] != 200:
            msg = '查询用户：' + src_uid + ' 直播信息失败，请检查拼写或者是API寄了\nError code：' + str(live_json["code"])
            await catch_str4.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询用户：' + src_uid + ' 直播信息失败，请检查拼写或者是API寄了'
        await catch_str4.finish(Message(f'{msg}'), reply_message=True)

    try:
        live_id = live_json['data']['lives'][int(live_index)]['liveId']
        username = live_json["data"]["channel"]["name"]
        room_id = str(live_json["data"]["channel"]["roomId"])
        totalLiveCount = str(live_json["data"]["channel"]["totalLiveCount"])
        totalDanmakuCount = str(live_json["data"]["channel"]["totalDanmakuCount"])
        totalIncome = str(live_json["data"]["channel"]["totalIncome"])
        totalLivehour = str(round(live_json["data"]["channel"]["totalLiveSecond"] / 60 / 60, 2))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询用户：' + src_uid + '失败,live_id解析失败,可能原因：场次数不对/无此场次'
        await catch_str4.finish(Message(f'{msg}'), reply_message=True)

    out_str = "#查收益 " + income_type_ch + "\n\n昵称:" + username + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UID:" + src_uid + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;房间号:" + room_id +\
             "\n\n 总直播数:" + totalLiveCount + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总弹幕数:" + totalDanmakuCount + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总收益:￥" + totalIncome + \
              "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总直播时长:" + totalLivehour + "h\n\n" + \
              "| 时间 | uid | 昵称 | 内容 | 价格 |\n" \
              "| :-----| :-----| :-----| :-----| :-----|\n"

    # nonebot.logger.info(out_str)

    # 获取当场直播信息
    url = 'https://danmakus.com/api/info/live?liveid=' + live_id + '&type=' + income_type + '&uid='
    info_json = await common_get_return_json(url)

    if info_json == None:
        msg = '查询用户：' + src_uid + ' 场次数据失败，API寄了喵'
        await catch_str4.finish(Message(f'{msg}'), reply_message=True)

    try:
        if info_json['code'] != 200:
            msg = '查询用户：' + src_uid + ' 场次数据失败，请检查拼写或者是API寄了\nError code：' + str(temp["code"])
            await catch_str4.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询用户：' + src_uid + ' 场次数据失败，请检查拼写或者是API寄了'
        await catch_str4.finish(Message(f'{msg}'), reply_message=True)

    # 遍历弹幕信息
    for i in range(len(info_json["data"]["danmakus"])):
        out_str += "| {:<s} | {:<d} | {:<s} | {:<s} | ￥{:<.1f} |".format(
            await timestamp_to_date(info_json["data"]["danmakus"][i]["sendDate"]),
            info_json["data"]["danmakus"][i]["uId"],
            info_json["data"]["danmakus"][i]["name"],
            await filter_markdown(info_json["data"]["danmakus"][i]["message"]),
            info_json["data"]["danmakus"][i]["price"])
        out_str += '\n'
        # 2000条就算了吧，太多了
        if i >= 2000:
            break
    out_str += '\n数据源自：danmakus.com\n'
    # nonebot.logger.info("\n" + out_str)

    if len(info_json["data"]["danmakus"]) < 2000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str4.send(MessageSegment.image(output))
    else:
        msg = '果咩，礼物数大于2000，发不出去喵~（可修改源码增大上限）'
        await catch_str4.finish(Message(f'{msg}'), reply_message=True)


@catch_str5.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    username = ""

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到UID：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str5.finish(Message(f'{msg}'), reply_message=True)

    # 传入uid获取用户基本信息
    url = 'https://account.bilibili.com/api/member/getCardByMid?mid=' + content
    base_info_json = await common_get_return_json(url)

    if base_info_json == None:
        msg = '查询UID：' + content + '的用户信息失败，可能是网络问题或者API寄了喵'
        await catch_str5.finish(Message(f'{msg}'), reply_message=True)

    try:
        if base_info_json['code'] != 0:
            nonebot.logger.info(base_info_json)
            msg = '获取uid：' + content + '，用户信息失败。\nError code：' + str(base_info_json["code"])
            await catch_str5.finish(Message(f'{msg}'), reply_message=True)
        username = base_info_json["card"]["name"]
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '的用户名失败，请检查拼写/API寄了'
        await catch_str5.finish(Message(f'{msg}'), reply_message=True)

    url = 'https://api.vtbs.moe/v1/guard/' + content
    guard_info_json = await common_get_return_json(url)

    if guard_info_json == None:
        msg = '查询UID：' + content + '失败，API寄了喵，请进行问题排查~'
        await catch_str5.finish(Message(f'{msg}'), reply_message=True)

    try:
        guard_len = len(guard_info_json)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '失败，请检查拼写/没有舰团/API寄了'
        await catch_str5.finish(Message(f'{msg}'), reply_message=True)

    out_str = "#查舰团\n\n查询用户名:" + username + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UID:" + content + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;舰团数:" + str(guard_len) + "\n\n" + \
              "| 昵称 | UID | 舰团类型 |\n" \
              "| :-----| :-----| :-----|\n"
    try:
        for i in range(guard_len):
            uname = guard_info_json[i]['uname']
            mid = guard_info_json[i]['mid']
            if guard_info_json[i]['level'] == 0:
                level = '总督'
            elif guard_info_json[i]['level'] == 1:
                level = '提督'
            else:
                level = '舰长'
            out_str += "| {:<s} | {:<d} | {:<s} |".format(uname, mid, level)
            out_str += '\n'
        out_str += '\n数据源自：vtbs.moe\n'
        # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '失败，请检查拼写/没有舰团/API寄了'
        await catch_str5.finish(Message(f'{msg}'), reply_message=True)

    output = await md_to_pic(md=out_str, width=500)
    await catch_str5.send(MessageSegment.image(output))


# 查昵称
@catch_str6.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    url = 'https://api.bilibili.com/x/web-interface/search/type?page_size=10&keyword=' + content + \
                '&search_type=bili_user'
    info_json = await common_get_return_json(url)
    # nonebot.logger.info(info_json)

    if info_json == None:
        msg = '网络出问题了或者接口寄了喵~'
        await catch_str6.finish(Message(f'{msg}'), reply_message=True)

    try:
        result = info_json['data']['result']
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询无结果，请检查拼写或是接口寄了'
        await catch_str6.finish(Message(f'{msg}'), reply_message=True)

    msg = "\n 查询用户名：" + content + "\n" + \
          " 显示格式为：【 UID  昵称  粉丝数 】\n"
    for i in range(len(result)):
        msg += " 【 " + str(result[i]["mid"]) + "  " + result[i]["uname"] + "  " + str(result[i]["fans"]) + ' 】\n'
    await catch_str6.finish(Message(f'{msg}'), reply_message=True)


@catch_str7.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 分别传入 日/周/月榜 和 数量
    content = content.split()
    date_range = ''
    size = '100'

    if len(content) == 1:
        date_range = content[0]
    elif len(content) >= 2:
        date_range = content[0]
        size = content[1]

    await catch_str7.send("正在获取数据中，请耐心等待...", reply_message=True)

    date_ranges = ['月榜', '周榜', '日榜']
    if date_range in date_ranges:
        url = 'https://www.vtbs.fun:8050/rank/income?dateRange=' + await date_range_change(date_range) + '&current=1&size=' + size
        json1 = await common_get_return_json(url)
    else:
        msg = '命令错误，例如：【/营收 月榜】【/营收 周榜 10】【/营收 日榜 3】'
        await catch_str7.finish(Message(f'{msg}'), reply_message=True)

    if json1 == None:
        msg = '请求失败，可能是网络问题或者接口寄了喵~'
        await catch_str7.finish(Message(f'{msg}'), reply_message=True)

    try:
        if json1["code"] != 200:
            nonebot.logger.info(json1)
            msg = '请求失败，寄了喵。\nError code：' + str(json1["code"])
            await catch_str7.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '请求解析失败，接口寄了喵'
        await catch_str7.finish(Message(f'{msg}'), reply_message=True)

    try:
        out_str = "#VTB营收" + date_range + "\n" + \
                  "| 用户名 | uid | 营收 | 付费人数 | 弹幕总数 | 直播时长 |\n" \
                  "| :-----| :-----| :-----| :-----| :-----| :-----|\n"
        for i in range(len(json1['data'])):
            name = json1['data'][i]['name']
            danmaku = json1['data'][i]['danmaku']
            gold_user = json1['data'][i]['goldUser']
            income = json1['data'][i]['income']
            mid = json1['data'][i]['mid']
            live_time = json1['data'][i]['liveTime']

            out_str += '| ' + name + ' | ' + str(mid) + ' | '
            if income >= 10000000:
                income = round(income / 10000000, 2)
                out_str += str(income) + '万 | '
            else:
                income = round(income / 1000, 2)
                out_str += str(income) + '元 | '
            out_str += str(gold_user) + '人 | ' + str(danmaku) + '条 | '
            live_time = round(live_time / 60 / 60, 2)
            out_str += str(live_time) + 'h |' + '\n'

        out_str += "\n\n数据源自：vtbs.fun"
        # nonebot.logger.info("\n" + out_str)

        output = await md_to_pic(md=out_str, width=900)
        # 如果需要保存到本地则去除下面2行注释
        # output = Image.open(BytesIO(img))
        # output.save("md2pic.png", format="PNG")
        await catch_str7.send(MessageSegment.image(output))
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '数据解析失败，寄了喵（请查看日志排查问题）'
        await catch_str7.finish(Message(f'{msg}'), reply_message=True)


# VTB涨粉
@catch_str9.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 分别传入 日/周/月榜 和 数量
    content = content.split()
    date_range = ''
    size = '100'

    if len(content) == 1:
        date_range = content[0]
    elif len(content) >= 2:
        date_range = content[0]
        size = content[1]

    await catch_str9.send("正在获取数据中，请耐心等待...", reply_message=True)

    date_ranges = ['月榜', '周榜', '日榜']
    if date_range in date_ranges:
        url = 'https://www.vtbs.fun:8050/rank/incfans?dateRange=' + await date_range_change(date_range) + '&current=1&size=' + size
        # 获取数据喵
        json1 = await common_get_return_json(url)
    else:
        msg = '命令错误，例如：【/涨粉 月榜】【/涨粉 周榜 10】【/涨粉 日榜 3】'
        await catch_str9.finish(Message(f'{msg}'), reply_message=True)

    if json1 == None:
        msg = '请求失败，可能是网络问题或者接口寄了喵~'
        await catch_str9.finish(Message(f'{msg}'), reply_message=True)

    try:
        if json1["code"] != 200:
            nonebot.logger.info(json1)
            msg = '请求失败，寄了喵。\n接口返回：\nError code：' + str(json1["code"])
            await catch_str9.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        msg = '请求解析失败，接口寄了喵'
        nonebot.logger.info(e)
        await catch_str9.finish(Message(f'{msg}'), reply_message=True)

    try:
        out_str = "#VTB涨粉" + date_range + "\n" + \
                  "| 用户名 | uid | 涨粉 | 粉丝数 | 舰长数 | 播放量 |\n" \
                  "| :-----| :-----| :-----| :-----| :-----| :-----|\n"
        for i in range(len(json1['data'])):
            archiveView = json1['data'][i]['archiveView']
            fans = json1['data'][i]['fans']
            guards = json1['data'][i]['guards']
            incFans = json1['data'][i]['incFans']
            mid = json1['data'][i]['mid']
            name = json1['data'][i]['name']

            out_str += '| ' + name + ' | ' + str(mid) + ' | ' + str(incFans) + ' | '
            if fans > 10000:
                fans = round(fans / 10000, 2)
                out_str += str(fans) + '万 | '
            else:
                fans = round(fans, 2)
                out_str += str(fans) + ' | '
            out_str += str(guards) + ' | '
            if archiveView >= 100000000:
                archiveView = round(archiveView / 100000000, 2)
                out_str += str(archiveView) + '亿 |'
            elif archiveView >= 10000:
                archiveView = round(archiveView / 10000, 2)
                out_str += str(archiveView) + '万 |'
            else:
                archiveView = round(archiveView, 2)
                out_str += str(archiveView) + ' |'

            out_str += '\n'

        out_str += "\n\n数据源自：vtbs.fun"
        # nonebot.logger.info("\n" + out_str)

        output = await md_to_pic(md=out_str, width=900)
        # 如果需要保存到本地则去除下面2行注释
        # output = Image.open(BytesIO(img))
        # output.save("md2pic.png", format="PNG")
        await catch_str9.send(MessageSegment.image(output))
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '数据解析失败，寄了喵（请查看日志排查问题）'
        await catch_str9.finish(Message(f'{msg}'), reply_message=True)


@catch_str8.handle()
async def _(bot: Bot, event: Event):
    msg = 'VTB数据看板：https://ikaros-521.gitee.io/vtb_data_board/' \
        '\nmatsuri：https://matsuri.icu/' \
        '\ndanmakus：https://danmakus.com/' \
        '\nvtbs.fun：http://www.vtbs.fun/' \
        '\nbiligank：https://biligank.com/' \
        '\n火龙榜：https://huolonglive.com/#/' \
        '\nvtbs.moe：https://vtbs.moe/' \
        '\nvup.loveava.top：https://vup.loveava.top/ranking' \
        '\nddstats：https://ddstats.ericlamm.xyz/' \
        '\nzeroroku：https://zeroroku.com/bilibili' \
        '\nlaplace：https://laplace.live/' \
        '\nstats.nailv：https://stats.nailv.live'
        
    await catch_str8.finish(Message(f'{msg}'), reply_message=True)


# DD风云榜
@catch_str10.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()
    num = '10'

    try:
        if len(content) != 0:
            num = str(int(content))
    except (KeyError, TypeError, IndexError) as e:
        num = '10'

    await catch_str10.send("正在获取数据中，请耐心等待...", reply_message=True)

    url = 'https://ddstats-api.ericlamm.xyz/stats?top=' + num
    json1 = await common_get_return_json(url)

    if json1 == None:
        msg = '请求失败，接口寄了喵'
        await catch_str10.finish(Message(f'{msg}'), reply_message=True)

    try:
        if json1["code"] != 200:
            nonebot.logger.info(json1)
            msg = '请求失败，寄了喵。\nError code：' + str(json1["code"])
            await catch_str10.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '请求解析失败，接口寄了喵'
        await catch_str10.finish(Message(f'{msg}'), reply_message=True)

    try:
        out_str = "#DD风云榜\n" + \
                  "##DD行为次数最多\n" + \
                  "| 用户名 | uid | DD行为次数 |\n" \
                  "| :-----| :-----| :-----|\n"
        for i in range(len(json1['data']['most_dd_behaviour_vups'])):
            name = json1['data']['most_dd_behaviour_vups'][i]['name']
            uid = json1['data']['most_dd_behaviour_vups'][i]['uid']
            count = json1['data']['most_dd_behaviour_vups'][i]['count']

            out_str += '| ' + name + ' | ' + str(uid) + ' | ' + str(count) + ' |'
            out_str += '\n'

        out_str += "\n##访问最多的直播间\n" + \
                   "| 用户名 | uid | 访问过n个不同的直播间 |\n" \
                   "| :-----| :-----| :-----|\n"
        for i in range(len(json1['data']['most_dd_vups'])):
            name = json1['data']['most_dd_vups'][i]['name']
            uid = json1['data']['most_dd_vups'][i]['uid']
            count = json1['data']['most_dd_vups'][i]['count']

            out_str += '| ' + name + ' | ' + str(uid) + ' | ' + str(count) + ' |'
            out_str += '\n'

        out_str += "\n##打赏金额最多\n" + \
                   "| 用户名 | uid | 打赏(元) |\n" \
                   "| :-----| :-----| :-----|\n"
        for i in range(len(json1['data']['most_spent_vups'])):
            name = json1['data']['most_spent_vups'][i]['name']
            uid = json1['data']['most_spent_vups'][i]['uid']
            spent = json1['data']['most_spent_vups'][i]['spent']

            out_str += '| ' + name + ' | ' + str(uid) + ' | ' + str(spent) + ' |'
            out_str += '\n'

        out_str += "\n\n数据源自：ddstats-api.ericlamm.xyz"
        # nonebot.logger.info("\n" + out_str)

        output = await md_to_pic(md=out_str, width=700)
        # 如果需要保存到本地则去除下面2行注释
        # output = Image.open(BytesIO(img))
        # output.save("md2pic.png", format="PNG")
        await catch_str10.send(MessageSegment.image(output))
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '数据解析失败，寄了喵（请查看日志排查问题）'
        await catch_str10.finish(Message(f'{msg}'), reply_message=True)


# 查牌子
@catch_str12.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    try:
        # 使用列表推导式和字典的 keys 方法来 检索匹配关键词的键值对
        keys = [key for d in DATA_MEDAL for key in d.keys() if content in key]
        values = [d[key] for d in DATA_MEDAL for key in d.keys() if content in key]
        # result = {key: value for key, value in zip(keys, values)}
        # json.dumps(result, indent=2, ensure_ascii=False)
        out_str = "#查牌子 " + content + "\n" + \
                  "| 牌子名 | 用户名 | uid | 房间号 |\n" \
                  "| :-----| :-----| :-----| :-----|\n"
        for key, value in zip(keys, values):
            medal_name = key
            name = value["uname"]
            uid = value["mid"]
            roomid = value["roomid"]

            out_str += '| ' + medal_name + ' | ' + name + ' | ' + str(uid) + ' | ' + str(roomid) + ' |'
            out_str += '\n'
        out_str += '\n\n数据源自：本地'

        output = await md_to_pic(md=out_str, width=700)
        await catch_str10.send(MessageSegment.image(output))
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '查询不到此牌子的数据（可能是数据不足或不存在此牌子喵~）'
        await catch_str12.finish(Message(f'{msg}'), reply_message=True)


# v详情
@catch_str13.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str13.finish(Message(f'{msg}'), reply_message=True)

    await catch_str13.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 1415, "height": 1920}) as page:
            await page.goto(
                "https://vtbs.moe/detail/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            await page.wait_for_selector('.el-row')
            await page.wait_for_timeout(10)
            await asyncio.sleep(10)
            temp_path = "./data/vtbs.moe_detail" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str13.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str13.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str13.finish(Message(f'{msg}'), reply_message=True)


# dmk查用户
@catch_str14.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"]) 
        await catch_str14.finish(Message(f'{msg}'), reply_message=True)

    await catch_str14.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 1040, "height": 2500}) as page:
            await page.goto(
                "https://danmakus.com/user/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/danmakus.com_user" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str14.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str14.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str14.finish(Message(f'{msg}'), reply_message=True)


# dmk查直播
@catch_str15.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str15.finish(Message(f'{msg}'), reply_message=True)

    await catch_str15.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 850, "height": 2000}) as page:
            await page.goto(
                "https://danmakus.com/channel/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/danmakus.com_channel" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str15.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str15.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str15.finish(Message(f'{msg}'), reply_message=True)


# blg查弹幕
@catch_str16.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str16.finish(Message(f'{msg}'), reply_message=True)

    await catch_str16.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_dm?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/biligank.com_ablive_dm" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str16.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str16.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str16.finish(Message(f'{msg}'), reply_message=True)


# blg查入场
@catch_str17.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str17.finish(Message(f'{msg}'), reply_message=True)

    await catch_str17.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_en?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/biligank.com_ablive_en" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str17.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str17.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str17.finish(Message(f'{msg}'), reply_message=True)


# blg查礼物
@catch_str18.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str18.finish(Message(f'{msg}'), reply_message=True)

    await catch_str18.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_gf?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/biligank.com_ablive_gf" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str18.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str18.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str18.finish(Message(f'{msg}'), reply_message=True)


# blg直播记录
@catch_str19.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str19.finish(Message(f'{msg}'), reply_message=True)

    await catch_str19.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 1000, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/tp?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/biligank.com_ablive_tp" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str19.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str19.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str19.finish(Message(f'{msg}'), reply_message=True)


# blg直播间sc
@catch_str20.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str20.finish(Message(f'{msg}'), reply_message=True)

    await catch_str20.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 1000, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_sc?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/biligank.com_ablive_sc" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str20.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str20.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str20.finish(Message(f'{msg}'), reply_message=True)


# icu查直播
@catch_str21.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str21.finish(Message(f'{msg}'), reply_message=True)

    await catch_str21.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 1200, "height": 300}) as page:
            await page.goto(
                "https://matsuri.icu/channel/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/matsuri.icu_channel" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str21.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str21.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str21.finish(Message(f'{msg}'), reply_message=True)


# 查人气
@catch_str22.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str22.finish(Message(f'{msg}'), reply_message=True)

    try:
        url = 'https://api.vtbs.moe/v1/detail/' + content
        data_json = await common_get_return_json(url)

        if data_json == None:
            msg = '查询不到：' + content + ' 的相关信息。\n可能是网络问题或API寄了或是vtbs.moe没有收录喵，可以自行去官网添加。'
            await catch_str22.finish(Message(f'{msg}'), reply_message=True)

        msg = "UID:" + content + "\n最近一场直播的人气峰值：" + str(data_json["lastLive"]["online"])
        await catch_str22.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '查询失败喵（看看后台日志吧）'
        await catch_str22.finish(Message(f'{msg}'), reply_message=True)


# lap查用户
@catch_str23.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str23.finish(Message(f'{msg}'), reply_message=True)

    await catch_str23.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 758, "height": 300}) as page:
            await page.goto(
                "https://laplace.live/user/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            # 等待页面加载完成
            await page.wait_for_selector('.jsx-5797876f0d745d6c')
            # 删除小作文
            click_js = 'let p_arr=document.getElementsByClassName("Home_xl__sAgvD")[0].getElementsByTagName("p");for(let i=0;i<(p_arr.length-1);i++){setTimeout(function(){p_arr[0].remove()},100)}'
            # 执行 JavaScript 代码
            result = await page.evaluate(click_js)
            click_js = 'let details=document.getElementsByClassName("jsx-5797876f0d745d6c Home_scrollableContent__6y8XH Home_xl__sAgvD")[0].getElementsByTagName("details");' \
                'let len=details.length;for(var i=0;i<len;i++){details[i].getElementsByTagName("summary")[0].click();};' \
                'document.getElementsByClassName("player")[0].remove();'
            # 执行 JavaScript 代码
            result = await page.evaluate(click_js)
            nonebot.logger.debug(result)
            # 修改长度已显示
            await page.wait_for_selector('.following-list')
            click_js = 'let len=document.getElementsByClassName("jsx-5797876f0d745d6c following-list").length;for(var i=0;i<len;i++){document.getElementsByClassName("jsx-5797876f0d745d6c following-list")[i].style.maxHeight="2000px"}'
            result = await page.evaluate(click_js)
            nonebot.logger.debug(result)
            await asyncio.sleep(3)
            temp_path = "./data/laplace.live_user" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str23.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str23.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str23.finish(Message(f'{msg}'), reply_message=True)


# lap查牌子
@catch_str24.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str24.finish(Message(f'{msg}'), reply_message=True)

    url = 'https://laplace.live/api/user-medals/' + content
    data_json = await common_get_return_json(url)

    if data_json == None:
        msg = '查询UID：' + content + '的数据失败，请检查拼写/API寄了'
        await catch_str24.finish(Message(f'{msg}'), reply_message=True)

    # nonebot.logger.info(data_json)

    out_str = "#lap查牌子\n\n查询用户名:" + data_json["data"]["name"] + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UID:" + content + "\n\n" + \
              "| 主播名 | UID | 牌子名 | 等级 |\n" \
              "| :-----| :-----| :-----| :-----|\n"
    try:
        for i in range(len(data_json["data"]["list"])):
            target_name = data_json["data"]["list"][i]["target_name"]
            target_id = data_json["data"]["list"][i]["medal_info"]["target_id"]
            medal_name = data_json["data"]["list"][i]["medal_info"]["medal_name"]
            level = data_json["data"]["list"][i]["medal_info"]["level"]
            
            out_str += "| {:<s} | {:<d} | {:<s} | {:<d} |".format(target_name, target_id, medal_name, level)
            out_str += '\n'
        out_str += '\n数据源自：laplace.live\n'
        # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '失败，数据解析失败，请查看后台日志排查'
        await catch_str24.finish(Message(f'{msg}'), reply_message=True)

    output = await md_to_pic(md=out_str, width=800)
    await catch_str24.send(MessageSegment.image(output))


# lap查充电
@catch_str27.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str27.finish(Message(f'{msg}'), reply_message=True)

    url = 'https://edge-fetcher.xn--7dvy22i.com/api/bilibili/upower/' + content
    data_json = await common_get_return_json(url)

    if data_json == None:
        msg = '查询UID：' + content + '的数据失败，请检查拼写/API寄了'
        await catch_str27.finish(Message(f'{msg}'), reply_message=True)

    try:
        if data_json['code'] != 0:
            msg = '查询UID：' + content + '的数据失败，请检查拼写/API寄了\nError code：' + str(data_json["code"])
            await catch_str27.finish(Message(f'{msg}'), reply_message=True)
    except Exception as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '的数据失败，请检查拼写/API寄了\nError code：' + str(data_json["code"])
        await catch_str27.finish(Message(f'{msg}'), reply_message=True)

    # nonebot.logger.info(data_json)

    out_str = "#lap查充电\n\n查询UID：" + content + "\n\n" + \
              "| 排名 | 用户名 | UID | 天数 |\n" \
              "| :-----| :-----| :-----| :-----|\n"
    try:
        for i in range(len(data_json["data"]["rank_info"])):
            nickname = data_json["data"]["rank_info"][i]["nickname"]
            mid = data_json["data"]["rank_info"][i]["mid"]
            rank = data_json["data"]["rank_info"][i]["rank"]
            day = data_json["data"]["rank_info"][i]["day"]
            
            out_str += "| {:<d} | {:<s} | {:<d} | {:<d} |".format(rank, nickname, mid, day)
            out_str += '\n'
        out_str += '\n数据源自：laplace.live\n'
        # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '失败，数据解析失败，请查看后台日志排查'
        await catch_str27.finish(Message(f'{msg}'), reply_message=True)

    output = await md_to_pic(md=out_str, width=800)
    await catch_str27.send(MessageSegment.image(output))


# zero查用户
@catch_str25.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str25.finish(Message(f'{msg}'), reply_message=True)

    await catch_str25.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 300}) as page:
            await page.goto(
                "https://zeroroku.com/bilibili/author/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            ) 
            click_js = 'setTimeout(() => {document.getElementsByClassName("r-btn r-btn-md r-btn-filled bg-default-2")[0].click()}, 2500);'
            result = await page.evaluate(click_js)
            nonebot.logger.info(result)
            await asyncio.sleep(3)
            temp_path = "./data/zeroroku.com_author" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str25.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str25.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str25.finish(Message(f'{msg}'), reply_message=True)


# zero被关注
@catch_str28.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str28.finish(Message(f'{msg}'), reply_message=True)

    url = 'https://api.zeroroku.com/bilibili/author/famous-fans?mid=' + content
    data_json = await common_get_return_json(url)

    if data_json == None:
        msg = '查询UID：' + content + '的数据失败，请检查拼写/API寄了'
        await catch_str28.finish(Message(f'{msg}'), reply_message=True)

    try:
        if len(data_json) == 0:
            msg = '查询UID：' + content + '，无被关注数据，over~'
            await catch_str28.finish(Message(f'{msg}'), reply_message=True)
    except Exception as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '的数据失败，请检查拼写/API寄了\nError code：' + str(data_json["code"])
        await catch_str28.finish(Message(f'{msg}'), reply_message=True)

    # nonebot.logger.info(data_json)

    out_str = "#zero被关注\n\n查询UID：" + content + "\n\n" + \
              "| 用户名 | UID | 粉丝数 |\n" \
              "| :-----| :-----| :-----|\n"
    try:
        for i in range(len(data_json)):
            name = data_json[i]["name"]
            mid = data_json[i]["mid"]
            fans = data_json[i]["fans"]
            
            out_str += "| {:<s} | {:<d} | {:<d} |".format(name, mid, fans)
            out_str += '\n'
        out_str += '\n数据源自：zeroroku.com\n'
        # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '查询UID：' + content + '失败，数据解析失败，请查看后台日志排查'
        await catch_str28.finish(Message(f'{msg}'), reply_message=True)

    output = await md_to_pic(md=out_str, width=600)
    await catch_str28.send(MessageSegment.image(output))


# v直播势
@catch_str29.handle()
async def _(bot: Bot, event: Event):
    await catch_str29.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 950, "height": 3000}) as page:
            await page.goto(
                "https://vtbs.moe/live",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/vtbs.moe_live" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str29.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str29.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str29.finish(Message(f'{msg}'), reply_message=True)


# v急上升
@catch_str30.handle()
async def _(bot: Bot, event: Event):
    await catch_str30.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 950, "height": 3000}) as page:
            await page.goto(
                "https://vtbs.moe/rise",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/vtbs.moe_rise" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str30.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str30.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str30.finish(Message(f'{msg}'), reply_message=True)


# v急下降
@catch_str31.handle()
async def _(bot: Bot, event: Event):
    await catch_str31.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 950, "height": 3000}) as page:
            await page.goto(
                "https://vtbs.moe/drop",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/vtbs.moe_drop" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str31.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str31.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str31.finish(Message(f'{msg}'), reply_message=True)


# v舰团
@catch_str32.handle()
async def _(bot: Bot, event: Event):
    await catch_str32.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 950, "height": 3000}) as page:
            await page.goto(
                "https://vtbs.moe/guard",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            temp_path = "./data/vtbs.moe_guard" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str32.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str32.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str32.finish(Message(f'{msg}'), reply_message=True)


# VDD风云榜
@catch_str33.handle()
async def _(bot: Bot, event: Event):
    await catch_str33.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 950, "height": 20000}) as page:
            await page.goto(
                "https://vtbs.moe/dd",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            await page.wait_for_selector('.columns')
            temp_path = "./data/vtbs.moe_dd" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str33.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str33.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str33.finish(Message(f'{msg}'), reply_message=True)


# V宏观
@catch_str34.handle()
async def _(bot: Bot, event: Event):
    await catch_str34.send("正在获取数据中，请耐心等待...\n(数据加载较慢，至少30秒以上)")

    try:
        async with get_new_page(viewport={"width": 950, "height": 2500}) as page:
            await page.goto(
                "https://vtbs.moe/macro",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            # 渲染很慢，建议多等等，等待个30秒
            await page.wait_for_timeout(30)
            await asyncio.sleep(30)
            temp_path = "./data/vtbs.moe_macro" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str34.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str34.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str34.finish(Message(f'{msg}'), reply_message=True)


# 查装扮
@catch_str35.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str35.finish(Message(f'{msg}'), reply_message=True)

    try:
        # 默认第一页 100个（应该够了）
        url = 'https://app.bilibili.com/x/v2/space/garb/list?pn=1&ps=100&vmid=' + content
        json1 = await common_get_return_json(url)
    except Exception as e:
        nonebot.logger.info(e)
        msg = '请求失败，寄了喵（请查看日志排查问题）'
        await catch_str10.finish(Message(f'{msg}'), reply_message=True)

    if json1 == None:
        msg = '查询不到：' + content + ' 的相关信息。\n可能是网络问题或API寄了'
        await catch_str35.finish(Message(f'{msg}'), reply_message=True)

    try:
        if json1["code"] != 0:
            nonebot.logger.info(json1)
            msg = '请求失败，寄了喵。\nError code：' + str(json1["code"])
            await catch_str35.finish(Message(f'{msg}'), reply_message=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '请求解析失败，接口寄了喵'
        await catch_str35.finish(Message(f'{msg}'), reply_message=True)

    try:
        out_str = "#查装扮\n查询UID：" + content + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;装扮总数：" + str(json1['data']['count']) + "\n\n" + \
                "| 装扮标题 | 粉丝号 | 装扮图数 | 标题背景图 |\n" \
                "| :-----| :-----| :-----| :-----|\n"
        for i in range(len(json1['data']['list'])):
            garb_title = json1['data']['list'][i]['garb_title']
            if 'fans_number' in json1['data']['list'][i]:
                fans_number = json1['data']['list'][i]['fans_number']
            else:
                fans_number = '无'
            img_count = str(len(json1['data']['list'][i]['images']))
            title_bg_image = json1['data']['list'][i]['title_bg_image']

            out_str += '| ' + garb_title + ' | ' + fans_number + ' | ' + img_count + \
                ' | ' + '![title_bg_image](' + title_bg_image + ')' + ' |'
            out_str += '\n'

        # nonebot.logger.info("\n" + out_str)

        output = await md_to_pic(md=out_str, width=1000)
        await catch_str35.send(MessageSegment.image(output))
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '数据解析失败，寄了喵（请查看日志排查问题）'
        await catch_str35.finish(Message(f'{msg}'), reply_message=True)


# LAPDD排行榜
@catch_str36.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()
    radio_sort = "radio-sort-price"

    content = content.split()

    if len(content) > 1:
        msg = '传参错误，命令格式【/lapdd 搜索类型(默认0: 月供，1: 总督，2: 提督，3：舰长)】'
        await catch_str36.finish(Message(f'{msg}'), reply_message=True)
    elif len(content) == 0:
        content = ["月供"]

    # 默认0: 月供，1: 总督，2: 提督，3：舰长
    RADIO_SORTS = {
        "月供": "radio-sort-price",
        "总督": "radio-sort-t1",
        "提督": "radio-sort-t2",
        "舰长": "radio-sort-t3",
        "0": "radio-sort-price",
        "1": "radio-sort-t1",
        "2": "radio-sort-t2",
        "3": "radio-sort-t3"
    }
    # 使用get()方法来获取字典中对应的值，如果找不到则返回默认值
    radio_sort = RADIO_SORTS.get(content[0], "radio-sort-price")

    await catch_str36.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        async with get_new_page(viewport={"width": 530, "height": 29999}) as page:
            await page.goto(
                "https://laplace.live/dd",
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            await page.wait_for_selector('.jsx-a9b5b32e4de3b53c')
            click_js = 'document.getElementById("' + radio_sort + '").click();document.getElementById("showVup").click()'
            # 执行 JavaScript 代码
            result = await page.evaluate(click_js)
            nonebot.logger.debug(result)
            await page.wait_for_selector('.item')
            # 渲染比较慢，建议多等等，等待个10秒
            await page.wait_for_timeout(10)
            await asyncio.sleep(10)
            temp_path = "./data/laplace.live_dd" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=False, path=temp_path)

        await catch_str36.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str36.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str36.finish(Message(f'{msg}'), reply_message=True)


# 斗虫  主播PK
@catch_str37.handle()
async def _(bot: Bot, event: Event, state: T_State):
    # 用命名分组获取数据
    # option = state["_matched_dict"]["option"]
    usernames = state["_matched_dict"]["usernames"].split() # 把用户名按空格分割成列表
    start_offset = state["_matched_dict"]["start_offset"]
    end_offset = state["_matched_dict"]["end_offset"]

    user_ids = []

    # print(usernames)
    # print(start_offset)
    # print(end_offset)

    # 判断是否传入日期偏移值
    if not start_offset or not end_offset:
        # 没有传入日期偏移值 默认前天到今天
        start_offset = "30"
        end_offset = "0"

    # 遍历用户数字
    for username in usernames:
        # 获取用户的uid
        temp = await data_preprocess(username)
        if 0 == temp["code"]:
            user_ids.append(temp["uid"])
        else:
            nonebot.logger.info(temp)
            msg = '查询不到：' + username + ' 的相关信息。\nError code：' + str(temp["code"])
            await catch_str37.finish(Message(f'{msg}'), reply_message=True)

    if len(user_ids) <= 1:
        msg = '传入用户数少于2，请多传几个喵~'
        await catch_str37.finish(Message(f'{msg}'), reply_message=True)

    await catch_str37.send("正在获取数据中，请耐心等待...", reply_message=True)

    try:
        query_params = {
            "streamers": user_ids,
            "beginDate": await get_date_str_with_offset(start_offset),
            "endDate": await get_date_str_with_offset(end_offset),
        }
        query_str = "&".join(f"streamers={id}" for id in query_params["streamers"])
        query_str += f"&beginDate={query_params['beginDate']}&endDate={query_params['endDate']}"
        url = f"https://stats.nailv.live/compare/arena?{query_str}"

        nonebot.logger.info("请求：" + url)

        async with get_new_page(viewport={"width": 940, "height": 5000}) as page:
            await page.goto(
                url=url,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            await page.wait_for_selector('.v-data-table__wrapper', timeout=60 * 1000)
            click_js = 'try{document.getElementById("app-bar").remove()}catch(e){console.log(e)}'
            # 执行 JavaScript 代码
            result = await page.evaluate(click_js)
            nonebot.logger.debug(result)
            # 渲染比较慢，建议多等等，等待个3秒
            await page.wait_for_timeout(3)
            await asyncio.sleep(3)
            temp_path = "./data/stats.nailv.live_compare" + await get_current_timestamp_seconds() + ".png"
            pic = await page.screenshot(full_page=True, path=temp_path)

        await catch_str37.finish(MessageSegment.image(pic))
    except TimeoutError as e:
        nonebot.logger.info(e)
        msg = '打开页面超时喵~可能是网络问题或是对面寄了'
        await catch_str37.finish(Message(f'{msg}'), reply_message=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '打开页面失败喵（看看后台日志吧）'
        await catch_str37.finish(Message(f'{msg}'), reply_message=True)


# eh查直播
@catch_str38.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text().strip()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '查询不到用户名为：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str38.finish(Message(f'{msg}'), reply_message=True)

    try:
        msg = MessageSegment.image(file=("http://eihei.gendaimahou.net/listen/livepic.php?uid=" + content))
        await catch_str38.finish(Message(msg))
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = "发送失败，请检查后台日志排查问题喵~"
        await catch_str38.finish(Message(f'{msg}'), reply_message=True)



# 日/周/月榜转Unicode
async def date_range_change(date_range):
    if date_range == '日榜':
        return '%E6%97%A5%E6%A6%9C'
    elif date_range == '周榜':
        return '%E5%91%A8%E6%A6%9C'
    elif date_range == '月榜':
        return '%E6%9C%88%E6%A6%9C'
    else:
        return '%E6%9C%88%E6%A6%9C'


# 数据预处理 返回uid 如果返回-1为异常 -2表示搜索成功但没有相关用户
async def data_preprocess(content):
    temp = {"code": 0, "uid": content, "resp": ""}
    # 由于逻辑问题 查uid时需要追加(以:或：或uid:或UID:或uid：打头)在命令后
    if content.startswith("uid:") or content.startswith("UID:") or content.startswith("uid："):
        temp["uid"] = content[4:]
        return temp
    elif content.startswith(":") or content.startswith("："):
        temp["uid"] = content[1:]
        return temp
    else:
        # 遍历本地DATA
        for i in range(len(DATA)):
            # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
            try:
                if content == DATA[i]["uname"]:
                    temp["uid"] = str(DATA[i]["mid"])
                    return temp
            except (KeyError, TypeError, IndexError) as e:
                continue

        # 通过昵称查询uid，默认只查搜索到的第一个用户
        url = 'https://api.bilibili.com/x/web-interface/search/type?page_size=10&keyword=' + content + \
                '&search_type=bili_user'
        info_json = await common_get_return_json(url)
        # nonebot.logger.info(info_json)

        if info_json == None:
            temp["resp"] = "None"
            temp["code"] = -1
            nonebot.logger.info("请求失败，请排查cookie是否配置，或者接口寄了或其他问题")
            return temp

        try:
            if info_json['code'] != 0:
                temp["code"] = -1
                nonebot.logger.info(info_json)
                return temp

            if "result" in info_json['data']:
                result = info_json['data']['result']
                # 只获取第一个搜索结果的数据
                temp["uid"] = str(result[0]["mid"])
                return temp
            
            temp["code"] = -2
            nonebot.logger.info(info_json)
            return temp
        except (KeyError, TypeError, IndexError) as e:
            temp["resp"] = json.dumps(info_json, ensure_ascii=False)
            temp["code"] = -1
            nonebot.logger.info("查询不到用户名为：" + content + " 的相关信息。异常：" + str(e) + '\n' + temp["resp"])
            return temp


# 传入uid获取用户直播间房间号
async def get_room_id(uid):
    url = 'https://api.live.bilibili.com/room/v2/Room/room_id_by_uid?uid=' + uid
    ret = await common_get_return_json(url)

    if ret == None:
        return 0

    try:
        room_id = ret['data']['room_id']
    except TypeError:
        nonebot.logger.info("get_room_id " + str(uid) + "失败，code=" + str(ret['code']))
        return 0
    return room_id


# 通用get请求返回json
async def common_get_return_json(url, headers=header1, timeout=60):
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url, headers=headers, timeout=timeout) as response:
                result = await response.read()
                ret = json.loads(result)
    except:
        return None
    # nonebot.logger.info(ret)
    return ret


# 时间戳转换
async def timestamp_to_date(timestamp):
    # 转换成localtime
    time_local = time.localtime(timestamp / 1000)
    # 转换成新的时间格式(精确到秒)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt  # 2021-11-09 09:46:48


# markdown特殊字符过滤，并当字符串每超过20个时，在其后插入一个<br>
async def filter_markdown(text):
    filtered_text = re.sub(r'[_*#->`]', '', text)
    return re.sub(r"(.{20})", r"\1<br>", filtered_text, 0, re.DOTALL)


# 获取时间戳的当前的秒
async def get_current_timestamp_seconds():
    current_timestamp = int(time.time())
    return str(current_timestamp % 60)


# 获取年月日（y-m-d）字符串，可以传入日期偏移值
async def get_date_str_with_offset(offset):
    # 获取今天的日期对象
    today = datetime.date.today()
    # 根据偏移值创建时间差对象
    delta = datetime.timedelta(days=int(offset))
    # 计算偏移后的日期对象
    target_date = today - delta
    # 将日期对象转换为字符串格式
    date_str = target_date.strftime("%Y-%m-%d")
    return date_str
