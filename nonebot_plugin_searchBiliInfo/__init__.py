import json
import re
import nonebot
import aiohttp
import time
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.typing import T_State
from nonebot.params import CommandArg
from nonebot.exception import FinishedException

from nonebot_plugin_htmlrender import (
    md_to_pic,
    get_new_page,
)

from .data import DATA
from .data_medal import DATA_MEDAL

from nonebot.plugin import PluginMetadata


help_text = f"""
插件功能：
/查 昵称关键词或uid(uid需要以:或：或uid:或UID:或uid：打头)
/查直播 昵称关键词或uid 场次数（默认不写为全部）
/查舰团 昵称关键词或uid
/查昵称 昵称关键词或uid
/查收益 昵称关键词或uid 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)
/查观看 昵称关键词或uid
/查弹幕 查询的目标人昵称关键词或uid 查询的主播昵称关键词或uid 页数 条数
/查弹幕2 查询的目标人昵称关键词或uid 页数 条数
/营收 日/周/月榜 人数（不填默认100）
/涨粉 日/周/月榜 人数（不填默认100）
/DD风云榜 人数（不填默认10）
/查牌子 主播牌子关键词
/查人气 昵称关键词或uid
/vtb网站 或 /vtb资源 （大写也可以）
/v详情 昵称关键词或uid  （大写也可以）
/dmk查用户 昵称关键词或uid  （大写也可以）
/dmk查直播 昵称关键词或uid  （大写也可以）
/blg查弹幕 昵称关键词或uid  （大写也可以）
/blg查入场 昵称关键词或uid  （大写也可以）
/blg查礼物 昵称关键词或uid  （大写也可以）
/blg直播记录 昵称关键词或uid  （大写也可以）
/blg直播间sc 昵称关键词或uid  （大写也可以）
/icu查直播 昵称关键词或uid  （大写也可以）


调用的相关API源自b站官方接口、danmakus.com、ddstats.ericlamm.xyz、biligank.com和vtbs.fun
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
catch_str3 = on_command("查直播")
catch_str4 = on_command('查收益')
catch_str5 = on_command('查舰团')
catch_str6 = on_command('查昵称')
catch_str7 = on_command('营收')
catch_str9 = on_command('涨粉')
catch_str8 = on_command("vtb网站", aliases={"VTB网站", "Vtb网站", "vtb资源", "VTB资源"})
catch_str10 = on_command('DD风云榜', aliases={"风云榜", "dd风云榜"})
catch_str12 = on_command('查牌子')
catch_str13 = on_command('V详情', aliases={"v详情"})
catch_str14 = on_command('dmk查用户', aliases={"DMK查用户", "danmakus查用户"})
catch_str15 = on_command('dmk查直播', aliases={"DMK查直播", "danmakus查直播"})
catch_str16 = on_command('blg查弹幕', aliases={"BLG查弹幕", "biligank查弹幕"})
catch_str17 = on_command('blg查入场', aliases={"BLG查入场", "biligank查入场"})
catch_str18 = on_command('blg查礼物', aliases={"BLG查礼物", "biligank查礼物"})
catch_str19 = on_command('blg直播记录', aliases={"BLG直播记录", "biligank直播记录"})
catch_str20 = on_command('blg直播间sc', aliases={"BLG直播间sc", "blg直播间SC", "BLG直播间SC", "biligank直播间sc"})
catch_str21 = on_command('icu查直播', aliases={"ICU查直播", "matsuri查直播"})
catch_str22 = on_command('查人气')


@catch_str.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到用户名为：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    # 传入uid获取用户基本信息
    base_info_json = await get_base_info(content)
    # 获取用户信息失败
    if base_info_json['code'] != 0:
        nonebot.logger.info(base_info_json)
        msg = '\n获取uid：' + content + '，用户信息失败。\nError code：' + str(base_info_json['code'])
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    # 获取用户直播间id
    room_id = await get_room_id(content)
    # 没有直播间 默认为0
    if room_id == 0:
        guard_info_json = {"data": {"info": {"num": 0}}}
    else:
        guard_info_json = await get_guard_info(content, room_id)

    try:
        msg = '\n用户名：' + base_info_json['card']['name'] + '\nUID：' + str(base_info_json['card']['mid']) + \
            '\n房间号：' + str(room_id) + '\n粉丝数：' + str(base_info_json['card']['fans']) + '\n舰团数：' + str(
            guard_info_json['data']['info']['num'])
    except:
        msg = "\n数据解析异常，请重试。（如果多次重试都失败，建议提issue待开发者修复）"
    await catch_str.finish(Message(f'{msg}'), at_sender=True)


@catch_str1.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid 目标uid 页数 条数
    content = content.split()
    src_uid = ""
    tgt_uid = ""
    page = "0"
    page_size = "3"

    if len(content) > 1:
        src_uid = content[0]
        tgt_uid = content[1]
    else:
        msg = '传参错误，命令格式【/查弹幕 用户uid 目标uid 页数(可不填，默认0) 条数(可不填，默认3)】'
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)

    if len(content) == 3:
        page = content[2]
    elif len(content) > 3:
        page = content[2]
        page_size = content[3]

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        nonebot.logger.info(temp)
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)
    
    temp = await data_preprocess(tgt_uid)
    if 0 == temp["code"]:
        tgt_uid = temp["uid"]
    else:
        msg = '\n查询不到用户名为：' + tgt_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        nonebot.logger.info(temp)
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)

    nonebot.logger.debug("src_uid:" + src_uid + " tgt_uid:" + tgt_uid)

    info_json = await get_detail_info(src_uid, tgt_uid, page, page_size)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '\n查询出错。Error code：' + str(temp["code"])
            nonebot.logger.info(info_json)

            await catch_str1.finish(Message(f'{msg}'), at_sender=True)
            return
    except (KeyError, TypeError, IndexError) as e:
        msg = '\n果咩，查询信息失败喵~请检查拼写或者是API寄了'
        nonebot.logger.info(e)
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n返回数据解析异常，寄~（请查日志排查问题）'
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)

    # 随便定的一个上限值 可以自行修改
    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str1.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，弹幕数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)


@catch_str11.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid 页数 条数
    content = content.split()
    src_uid = ""
    tgt_uid = ""
    page = "0"
    page_size = "3"

    if len(content) >= 1:
        src_uid = content[0]
    else:
        msg = '\n传参错误，命令格式【/查弹幕2 用户uid 页数(可不填，默认0) 条数(可不填，默认3)】'
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)

    if len(content) == 2:
        page = content[1]
    elif len(content) > 2:
        page = content[1]
        page_size = content[2]

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)

    nonebot.logger.debug("src_uid:" + src_uid + " tgt_uid:" + tgt_uid)

    info_json = await get_detail_info(src_uid, tgt_uid, page, page_size)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '\n查询出错。接口返回：\n' + json.dumps(info_json, indent=2, ensure_ascii=False)
            await catch_str11.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n果咩，查询信息失败喵~请检查拼写或者是API寄了'
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n返回数据解析异常，寄~（请查日志排查问题）'
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)

    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str11.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，弹幕数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)


@catch_str2.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到用户名为：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    user_info_json = await get_user_info(content)

    try:
        # 判断返回代码
        if user_info_json['code'] != 200:
            msg = '\n查询用户：' + content + '失败'
            await catch_str2.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n果咩，查询用户信息失败喵~请检查拼写或者是API寄了'
        await catch_str2.finish(Message(f'{msg}'), at_sender=True)

    out_str = "#查观看\n\n查询用户UID：" + content + "\n\n" + \
              "| 昵称 | UID | 房间号 |\n" \
              "| :-----| :-----| :-----|\n"
    # 数据集合
    name_set = set()
    uId_set = set()
    roomId_set = set()

    for i in range(len(user_info_json['data'])):
        name = user_info_json['data'][i]['name']
        uId = user_info_json['data'][i]['uId']
        roomId = user_info_json['data'][i]['roomId']

        name_set.add(name)
        uId_set.add(uId)
        roomId_set.add(roomId)

    name_list = list(name_set)
    uId_list = list(uId_set)
    roomId_list = list(roomId_set)

    out_str += " 观看总数：" + str(len(name_set)) + "\n"
    # nonebot.logger.info(out_str)

    for i in range(len(name_set)):
        # nonebot.logger.info("i:=" + str(i) + "  | {:<s} | {:<d} | {:<d} |".format(name_list[i], uId_list[i], roomId_list[i]))
        out_str += "| {:<s} | {:<d} | {:<d} |".format(name_list[i], uId_list[i], roomId_list[i])
        out_str += '\n'
    out_str += '\n数据源自：danmakus.com\n'
    # nonebot.logger.info("\n" + out_str)

    if len(uId_set) < 1000:
        output = await md_to_pic(md=out_str, width=600)
        await catch_str2.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，dd数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str2.finish(Message(f'{msg}'), at_sender=True)


@catch_str3.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid 最近n场
    content = content.split()
    src_uid = ""
    info_size = "99999"

    if len(content) == 1:
        src_uid = content[0]
    elif len(content) > 1:
        src_uid = content[0]
        info_size = content[1]
    else:
        msg = '\n传参错误，命令格式【/查直播 用户uid 最近场次数】'
        await catch_str3.finish(Message(f'{msg}'), at_sender=True)

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    info_json = await get_info(src_uid)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '\n查询用户：' + src_uid + '失败，请检查拼写或者是API寄了\nError code：' + str(info_json["code"])
            await catch_str3.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询用户：' + src_uid + '失败，请检查拼写或者是API寄了'
        await catch_str3.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n解析数据异常（请查日志排查问题）'
        await catch_str3.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n果咩，直播数大于2000，发不出去喵~'
        await catch_str3.finish(Message(f'{msg}'), at_sender=True)


@catch_str4.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    # 以空格分割 用户uid 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)
    content = content.split()
    src_uid = ""
    live_index = "0"
    income_type = "1"

    if len(content) == 1:
        src_uid = content[0]
    elif len(content) == 2:
        src_uid = content[0]
        income_type = content[1]
    elif len(content) > 2:
        src_uid = content[0]
        income_type = content[1]
        live_index = content[2]
    else:
        msg = '\n传参错误，命令格式【/查直播 用户uid 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)】'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    live_json = await get_info(src_uid)

    try:
        # 判断返回代码
        if live_json['code'] != 200:
            msg = '\n查询用户：' + src_uid + ' 直播信息失败，请检查拼写或者是API寄了\nError code：' + str(live_json["code"])
            await catch_str4.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询用户：' + src_uid + ' 直播信息失败，请检查拼写或者是API寄了'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n查询用户：' + src_uid + '失败,live_id解析失败,可能原因：场次数不对/无此场次'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

    out_str = "#查收益\n\n昵称:" + username + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UID:" + src_uid + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;房间号:" + room_id +\
             "\n\n 总直播数:" + totalLiveCount + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总弹幕数:" + totalDanmakuCount + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总收益:￥" + totalIncome + \
              "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总直播时长:" + totalLivehour + "h\n\n" + \
              "| 时间 | uid | 昵称 | 内容 | 价格 |\n" \
              "| :-----| :-----| :-----| :-----| :-----|\n"

    # 默认1: 礼物，2: 上舰或舰长，3: SC
    if income_type == "礼物":
        income_type = "1"
    elif income_type == "上舰" or income_type == "舰长":
        income_type = "2"
    elif income_type == "SC" or income_type == "sc" or income_type == "Sc":
        income_type = "3"
    else:
        income_type = "1"

    # nonebot.logger.info(out_str + "income_type:" + income_type)

    # 获取当场直播信息
    info_json = await get_live_info(live_id, income_type)
    try:
        if info_json['code'] != 200:
            msg = '\n查询用户：' + src_uid + ' 场次数据失败，请检查拼写或者是API寄了\nError code：' + str(temp["code"])
            await catch_str4.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询用户：' + src_uid + ' 场次数据失败，请检查拼写或者是API寄了'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n果咩，礼物数大于2000，发不出去喵~（可修改源码增大上限）'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)


@catch_str5.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    username = ""

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到UID：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    base_info_json = await get_base_info(content)
    try:
        if base_info_json['code'] != 0:
            nonebot.logger.info(base_info_json)
            msg = '\n获取uid：' + content + '，用户信息失败。\nError code：' + str(base_info_json["code"])
            await catch_str.finish(Message(f'{msg}'), at_sender=True)
        username = base_info_json["card"]["name"]
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询UID：' + content + '的用户名失败，请检查拼写/API寄了'
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    guard_info_json = await get_user_guard(content)

    try:
        guard_len = len(guard_info_json)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询UID：' + content + '失败，请检查拼写/没有舰团/API寄了'
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

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
        msg = '\n查询UID：' + content + '失败，请检查拼写/没有舰团/API寄了'
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    output = await md_to_pic(md=out_str, width=500)
    await catch_str5.send(MessageSegment.image(output))


@catch_str6.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    info_json = await get_user_keyword_info(content)
    # nonebot.logger.info(info_json)

    try:
        result = info_json['data']['result']
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询无结果，请检查拼写或是接口寄了'
        await catch_str6.finish(Message(f'{msg}'), at_sender=True)

    msg = "\n 查询用户名：" + content + "\n" + \
          " 显示格式为：【 UID  昵称  粉丝数 】\n"
    for i in range(len(result)):
        msg += " 【 " + str(result[i]["mid"]) + "  " + result[i]["uname"] + "  " + str(result[i]["fans"]) + ' 】\n'
    await catch_str6.finish(Message(f'{msg}'), at_sender=True)


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

    date_ranges = ['月榜', '周榜', '日榜']
    if date_range in date_ranges:
        json1 = await get_revenue(date_range, size)
    else:
        msg = '\n命令错误，例如：【/营收 月榜】【/营收 周榜 10】【/营收 日榜 3】'
        await catch_str7.finish(Message(f'{msg}'), at_sender=True)

    try:
        if json1["code"] != 200:
            nonebot.logger.info(json1)
            msg = '\n请求失败，寄了喵。\nError code：' + str(json1["code"])
            await catch_str7.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n请求解析失败，接口寄了喵'
        await catch_str7.finish(Message(f'{msg}'), at_sender=True)

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
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n数据解析失败，寄了喵（请查日志排查问题）'
        await catch_str7.finish(Message(f'{msg}'), at_sender=True)


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

    date_ranges = ['月榜', '周榜', '日榜']
    if date_range in date_ranges:
        # 获取数据喵
        json1 = await get_incfans(date_range, size)
    else:
        msg = '\n命令错误，例如：【/涨粉 月榜】【/涨粉 周榜 10】【/涨粉 日榜 3】'
        await catch_str9.finish(Message(f'{msg}'), at_sender=True)

    try:
        if json1["code"] != 200:
            nonebot.logger.info(json1)
            msg = '\n请求失败，寄了喵。\n接口返回：\nError code：' + str(json1["code"])
            await catch_str9.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        msg = '\n请求解析失败，接口寄了喵'
        nonebot.logger.info(e)
        await catch_str9.finish(Message(f'{msg}'), at_sender=True)

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
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n数据解析失败，寄了喵（请查日志排查问题）'
        await catch_str9.finish(Message(f'{msg}'), at_sender=True)


@catch_str8.handle()
async def _(bot: Bot, event: Event, state: T_State):
    msg = '\nVTB数据看板：https://ikaros-521.gitee.io/vtb_data_board/' \
        '\nmatsuri：https://matsuri.icu/' \
        '\ndanmakus：https://danmakus.com/' \
        '\nvtbs.fun：http://www.vtbs.fun/' \
        '\nbiligank：https://biligank.com/' \
        '\n火龙榜：https://huolonglive.com/#/' \
        '\nvtbs.moe：https://vtbs.moe/' \
        '\nvup.loveava.top：https://vup.loveava.top/ranking' \
        '\nddstats：https://ddstats.ericlamm.xyz/' \
        '\nzeroroku：https://zeroroku.com/bilibili' \
        '\nlaplace：https://laplace.live/'
        
    await catch_str8.finish(Message(f'{msg}'), at_sender=True)


@catch_str10.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()
    num = '10'

    try:
        if len(content) != 0:
            num = str(int(content))
    except (KeyError, TypeError, IndexError) as e:
        num = '10'

    json1 = await get_ddstats_stats(num)

    try:
        if json1["code"] != 200:
            nonebot.logger.info(json1)
            msg = '\n请求失败，寄了喵。\nError code：' + str(json1["code"])
            await catch_str10.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n请求解析失败，接口寄了喵'
        await catch_str10.finish(Message(f'{msg}'), at_sender=True)

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
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n数据解析失败，寄了喵（请查日志排查问题）'
        await catch_str10.finish(Message(f'{msg}'), at_sender=True)


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
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查询不到此牌子的数据（可能是数据不足或不存在此牌子喵~）'
        await catch_str12.finish(Message(f'{msg}'), at_sender=True)


@catch_str13.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str13.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 1415, "height": 1920}) as page:
            await page.goto(
                "https://vtbs.moe/detail/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/vtbs.moe_detail.png")

        await catch_str13.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str13.finish(Message(f'{msg}'), at_sender=True)


@catch_str14.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"]) 
        await catch_str14.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 1040, "height": 2500}) as page:
            await page.goto(
                "https://danmakus.com/user/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/danmakus.com_user.png")

        await catch_str14.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str14.finish(Message(f'{msg}'), at_sender=True)


@catch_str15.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str15.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 850, "height": 2000}) as page:
            await page.goto(
                "https://danmakus.com/channel/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/danmakus.com_channel.png")

        await catch_str15.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str15.finish(Message(f'{msg}'), at_sender=True)


@catch_str16.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str16.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_dm?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/biligank.com_ablive_dm.png")

        await catch_str16.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str16.finish(Message(f'{msg}'), at_sender=True)


# blg查入场
@catch_str17.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str17.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_en?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/biligank.com_ablive_en.png")

        await catch_str17.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str17.finish(Message(f'{msg}'), at_sender=True)


# blg查礼物
@catch_str18.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str18.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 800, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_gf?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/biligank.com_ablive_gf.png")

        await catch_str18.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str18.finish(Message(f'{msg}'), at_sender=True)


# blg直播记录
@catch_str19.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str19.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 1000, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/tp?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/biligank.com_ablive_sc.png")

        await catch_str19.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str19.finish(Message(f'{msg}'), at_sender=True)


# blg直播间sc
@catch_str20.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str20.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 1000, "height": 200}) as page:
            await page.goto(
                "https://biligank.com/live/ablive_sc?offset=0&uid=" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/biligank.com_ablive_sc.png")

        await catch_str20.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str20.finish(Message(f'{msg}'), at_sender=True)


# icu查直播
@catch_str21.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str21.finish(Message(f'{msg}'), at_sender=True)

    try:
        async with get_new_page(viewport={"width": 1200, "height": 300}) as page:
            await page.goto(
                "https://matsuri.icu/channel/" + content,
                timeout=2 * 60 * 1000,
                wait_until="networkidle",
            )
            pic = await page.screenshot(full_page=True, path="./data/matsuri.icu_channel.png")

        await catch_str21.finish(MessageSegment.image(pic))
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.info(e)
        msg = '\n查打开页面失败喵（看看后台日志吧）'
        await catch_str21.finish(Message(f'{msg}'), at_sender=True)


# 查人气
@catch_str22.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    content = msg.extract_plain_text()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        nonebot.logger.info(temp)
        msg = '\n查询不到：' + content + ' 的相关信息。\nError code：' + str(temp["code"])
        await catch_str22.finish(Message(f'{msg}'), at_sender=True)

    try:
        data_json = await get_popularity(content)
        if data_json == None:
            msg = '\n查询不到：' + content + ' 的相关信息。\nvtbs.moe没有收录喵，可以自行去官网添加。'
            await catch_str22.finish(Message(f'{msg}'), at_sender=True)

        msg = "最近一场直播的人气峰值：" + str(data_json["lastLive"]["online"])
        await catch_str22.finish(Message(f'{msg}'), at_sender=True)
    except FinishedException:
        pass
    except Exception as e:
        nonebot.logger.info(e)
        msg = '\n查询失败喵（看看后台日志吧）'
        await catch_str22.finish(Message(f'{msg}'), at_sender=True)


# 获取主播直播峰值人气
async def get_popularity(uid):
    try:
        API_URL = 'https://api.vtbs.moe/v1/detail/' + uid
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                result = await response.read()
                ret = json.loads(result)
    except Exception as e:
        nonebot.logger.info(e)
        return None
    # nonebot.logger.info(ret)
    return ret

# 获取营收榜单信息 传入 日/周/月榜 和 数量
async def get_revenue(date_range, size):
    if date_range == '日榜':
        date_range = '%E6%97%A5%E6%A6%9C'
    elif date_range == '周榜':
        date_range = '%E5%91%A8%E6%A6%9C'
    elif date_range == '月榜':
        date_range = '%E6%9C%88%E6%A6%9C'
    else:
        date_range = '%E6%9C%88%E6%A6%9C'

    API_URL = 'https://www.vtbs.fun:8050/rank/income?dateRange=' + date_range + '&current=1&size=' + size
    # nonebot.logger.info("API_URL=" + API_URL)
    async with aiohttp.ClientSession(headers=header1) as session:
        async with session.get(url=API_URL, headers=header1) as response:
            ret = await response.json()
    # nonebot.logger.info(ret)
    return ret


# 获取涨粉榜单信息 传入 日/周/月榜 和 数量
async def get_incfans(date_range, size):
    if date_range == '日榜':
        date_range = '%E6%97%A5%E6%A6%9C'
    elif date_range == '周榜':
        date_range = '%E5%91%A8%E6%A6%9C'
    elif date_range == '月榜':
        date_range = '%E6%9C%88%E6%A6%9C'
    else:
        date_range = '%E6%9C%88%E6%A6%9C'

    API_URL = 'https://www.vtbs.fun:8050/rank/incfans?dateRange=' + date_range + '&current=1&size=' + size
    nonebot.logger.debug("API_URL=" + API_URL)
    async with aiohttp.ClientSession(headers=header1) as session:
        async with session.get(url=API_URL, headers=header1) as response:
            ret = await response.json()
    # nonebot.logger.info(ret)
    return ret


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
        info_json = await use_name_get_uid(content)
        # nonebot.logger.info(info_json)

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


# 传入uid获取用户基本信息
async def get_base_info(uid):
    try:
        API_URL = 'https://account.bilibili.com/api/member/getCardByMid?mid=' + uid
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                result = await response.read()
                ret = json.loads(result)
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 传入uid获取用户直播间房间号
async def get_room_id(uid):
    try:
        API_URL = 'https://api.live.bilibili.com/room/v2/Room/room_id_by_uid?uid=' + uid
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}

    try:
        room_id = ret['data']['room_id']
    except TypeError:
        nonebot.logger.info("get_room_id " + str(uid) + "失败，code=" + str(ret['code']))
        return 0
    return room_id


# 获取舰团信息
async def get_guard_info(uid, room_id):
    try:
        API_URL = 'https://api.live.bilibili.com/xlive/app-room/v2/guardTab/topList?roomid=' + str(
            room_id) + '&page=1&ruid=' + uid + '&page_size=0'
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    return ret


# 通过昵称查询用户信息
async def get_user_keyword_info(name):
    try:
        API_URL = 'https://api.bilibili.com/x/web-interface/search/type?page_size=10&keyword=' + name + \
                '&search_type=bili_user'
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 获取用户舰团信息
async def get_user_guard(uid):
    try:
        API_URL = 'https://api.vtbs.moe/v1/guard/' + uid
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return False
    # nonebot.logger.info(ret)
    return ret


# 查询用户互动过的直播间 (未去重
async def get_user_info(uid):
    try:
        API_URL = 'https://danmakus.com/api/search/user/channel?uid=' + uid
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 查询用户记录
async def get_detail_info(src_uid, tgt_uid, page, page_size):
    try:
        API_URL = 'https://danmakus.com/api/search/user/detail?uid=' + src_uid + '&target=' + tgt_uid + \
                '&pagenum=' + page + '&pagesize=' + page_size
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 查询主播信息
async def get_info(uid):
    try:
        API_URL = 'https://danmakus.com/api/info/channel?cid=' + uid
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 查询单次直播详细信息
async def get_live_info(live_id, income_type):
    try:
        API_URL = 'https://danmakus.com/api/info/live?liveid=' + live_id + '&type=' + income_type + '&uid='
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 通过昵称查询信息
async def use_name_get_uid(name):
    try:
        API_URL = 'https://api.bilibili.com/x/web-interface/search/type?page_size=10&keyword=' + name + \
                '&search_type=bili_user'
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1) as response:
                ret = await response.json()
    except:
        return {"code": 408}
    # nonebot.logger.info(ret)
    return ret


# 传入top数量 获取DD风云榜数据
async def get_ddstats_stats(num):
    try:
        API_URL = 'https://ddstats-api.ericlamm.xyz/stats?top=' + num
        async with aiohttp.ClientSession(headers=header1) as session:
            async with session.get(url=API_URL, headers=header1, timeout=30) as response:
                result = await response.read()
                ret = json.loads(result)
    except:
        return {"code": 408}
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
