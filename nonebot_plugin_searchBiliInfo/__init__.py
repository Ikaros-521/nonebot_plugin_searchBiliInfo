# import datetime
import json

import nonebot
# import requests
# import asyncio
import aiohttp
import time
# from io import BytesIO
from nonebot import on_keyword, on_command
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.typing import T_State
# from nonebot_plugin_imageutils import Text2Image
from nonebot_plugin_htmlrender import (
    text_to_pic,
    md_to_pic,
    template_to_pic,
    get_new_page,
)

from .data import DATA
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

调用的相关API源自b站官方接口、danmaku.suki.club和vtbs.fun
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

catch_str = on_keyword({'/查 '})


@catch_str.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[3:]

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        msg = '\n查询不到用户名为：' + content + ' 的相关信息。'
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    # 传入uid获取用户基本信息
    base_info_json = await get_base_info(content)
    # 获取用户信息失败
    if base_info_json['code'] != 0:
        msg = '\n获取uid：' + content + '，用户信息失败。\n接口返回：\n' + json.dumps(base_info_json, indent=2, ensure_ascii=False)
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


catch_str1 = on_keyword({'/查弹幕 '})


@catch_str1.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

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
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)
    
    temp = await data_preprocess(tgt_uid)
    if 0 == temp["code"]:
        tgt_uid = temp["uid"]
    else:
        msg = '\n查询不到用户名为：' + tgt_uid + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)

    nonebot.logger.debug("src_uid:" + src_uid + " tgt_uid:" + tgt_uid)

    info_json = await get_detail_info(src_uid, tgt_uid, page, page_size)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '\n查询出错。接口返回：\n' + json.dumps(info_json, indent=2, ensure_ascii=False)
            await catch_str1.finish(Message(f'{msg}'), at_sender=True)
            return
    except (KeyError, TypeError, IndexError) as e:
        msg = '\n果咩，查询信息失败喵~请检查拼写或者是API寄了'
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
            title = info_json['data']['data'][i]['live']['title']
            out_str += '| 标题 | ' + title + ' |\n'
            for j in range(len(info_json['data']['data'][i]['danmakus'])):
                date = await timestamp_to_date(info_json['data']['data'][i]['danmakus'][j]['sendDate'])
                if info_json['data']['data'][i]['danmakus'][j]['type'] in [0, 1, 2, 3]:
                    message = info_json['data']['data'][i]['danmakus'][j]['message']
                elif info_json['data']['data'][i]['danmakus'][j]['type'] == 4:
                    message = "【进入直播间】"
                else:
                    message = "【其他消息】"
                out_str += '| ' + str(date) + '| ' + message + '|\n'
                data_len += 1
            out_str += '| -- | -- |\n'
        out_str += '\n数据源自：danmaku.suki.club\n'
    # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
        msg = '\n返回数据解析异常，寄~（请查日志排查问题）'
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)

    # 随便定的一个上限值 可以自行修改
    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str1.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，弹幕数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str1.finish(Message(f'{msg}'), at_sender=True)


catch_str11 = on_keyword({'/查弹幕2 '})


@catch_str11.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[6:]

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
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)

    nonebot.logger.debug("src_uid:" + src_uid + " tgt_uid:" + tgt_uid)

    info_json = await get_detail_info(src_uid, tgt_uid, page, page_size)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '\n查询出错。接口返回：\n' + json.dumps(info_json, indent=2, ensure_ascii=False)
            await catch_str11.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
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
            title = info_json['data']['data'][i]['live']['title']
            out_str += '| 主播——标题 | ' + name + '——' + title + ' |\n'
            for j in range(len(info_json['data']['data'][i]['danmakus'])):
                date = await timestamp_to_date(info_json['data']['data'][i]['danmakus'][j]['sendDate'])
                if info_json['data']['data'][i]['danmakus'][j]['type'] in [0, 1, 2, 3]:
                    message = info_json['data']['data'][i]['danmakus'][j]['message']
                elif info_json['data']['data'][i]['danmakus'][j]['type'] == 4:
                    message = "【进入直播间】"
                else:
                    message = "【其他消息】"
                out_str += '| ' + str(date) + '| ' + message + '|\n'
                data_len += 1
            out_str += '| -- | -- |\n'
        out_str += '\n数据源自：danmaku.suki.club\n'
    # nonebot.logger.info("\n" + out_str)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
        msg = '\n返回数据解析异常，寄~（请查日志排查问题）'
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)

    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str11.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，弹幕数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str11.finish(Message(f'{msg}'), at_sender=True)


catch_str2 = on_keyword({'/查观看 '})


@catch_str2.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]
    id = event.get_user_id()

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        msg = '\n查询不到用户名为：' + content + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    user_info_json = await get_user_info(content)

    try:
        # 判断返回代码
        if user_info_json['code'] != 200:
            msg = '\n查询用户：' + content + '失败'
            await catch_str2.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
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
    out_str += '\n数据源自：danmaku.suki.club\n'
    # nonebot.logger.info("\n" + out_str)

    if len(uId_set) < 1000:
        output = await md_to_pic(md=out_str, width=600)
        await catch_str2.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，dd数大于1000，发不出去喵~（可自行修改源码中的数量上限）'
        await catch_str2.finish(Message(f'{msg}'), at_sender=True)


catch_str3 = on_keyword({'/查直播 '})


@catch_str3.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    id = event.get_user_id()
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

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
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    info_json = await get_info(src_uid)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            msg = '\n查询用户：' + src_uid + '失败，请检查拼写或者是API寄了'
            await catch_str3.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
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
        nonebot.logger.error(e)
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
    out_str += '\n数据源自：danmaku.suki.club\n'
    # nonebot.logger.info("\n" + out_str)

    if len(info_json["data"]["lives"]) < 2000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str3.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，直播数大于2000，发不出去喵~'
        await catch_str3.finish(Message(f'{msg}'), at_sender=True)


catch_str4 = on_keyword({'/查收益 '})


@catch_str4.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

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
        msg = '\n传参错误，命令格式【/查直播 收益类型(默认1: 礼物，2: 上舰，3: SC) 用户uid 倒叙第n场(从0开始)】'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

    temp = await data_preprocess(src_uid)
    if 0 == temp["code"]:
        src_uid = temp["uid"]
    else:
        msg = '\n查询不到用户名为：' + src_uid + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    live_json = await get_info(src_uid)

    try:
        # 判断返回代码
        if live_json['code'] != 200:
            msg = '\n查询用户：' + src_uid + ' 直播信息失败，请检查拼写或者是API寄了'
            await catch_str4.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
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
        nonebot.logger.error(e)
        msg = '\n查询用户：' + src_uid + '失败,live_id解析失败,可能原因：场次数不对/无此场次'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

    out_str = "#查收益\n\n昵称:" + username + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UID:" + src_uid + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;房间号:" + room_id +\
             "\n\n 总直播数:" + totalLiveCount + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总弹幕数:" + totalDanmakuCount + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总收益:￥" + totalIncome + \
              "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;总直播时长:" + totalLivehour + "h\n\n" + \
              "| 时间 | uid | 昵称 | 内容 | 价格|\n" \
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
            msg = '\n查询用户：' + src_uid + ' 场次数据失败，请检查拼写或者是API寄了'
            await catch_str4.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
        msg = '\n查询用户：' + src_uid + ' 场次数据失败，请检查拼写或者是API寄了'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)

    # 遍历弹幕信息
    for i in range(len(info_json["data"]["danmakus"])):
        out_str += "| {:<s} | {:<d} | {:<s} | {:<s} | ￥{:<.1f} |".format(
            await timestamp_to_date(info_json["data"]["danmakus"][i]["sendDate"]),
            info_json["data"]["danmakus"][i]["uId"],
            info_json["data"]["danmakus"][i]["name"],
            info_json["data"]["danmakus"][i]["message"],
            info_json["data"]["danmakus"][i]["price"])
        out_str += '\n'
        # 2000条就算了吧，太多了
        if i >= 2000:
            break
    out_str += '\n数据源自：danmaku.suki.club\n'
    # nonebot.logger.info("\n" + out_str)

    if len(info_json["data"]["danmakus"]) < 2000:
        output = await md_to_pic(md=out_str, width=1100)
        await catch_str4.send(MessageSegment.image(output))
    else:
        msg = '\n果咩，礼物数大于2000，发不出去喵~（可修改源码增大上限）'
        await catch_str4.finish(Message(f'{msg}'), at_sender=True)


catch_str5 = on_keyword({'/查舰团 '})


@catch_str5.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

    username = ""

    temp = await data_preprocess(content)
    if 0 == temp["code"]:
        content = temp["uid"]
    else:
        msg = '\n查询不到UID：' + content + ' 的相关信息。\n接口返回：\n' + temp["resp"]
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    base_info_json = await get_base_info(content)
    try:
        if base_info_json['code'] != 0:
            msg = '\n获取uid：' + content + '，用户信息失败。\n接口返回：\n' + json.dumps(base_info_json, indent=2, ensure_ascii=False)
            await catch_str.finish(Message(f'{msg}'), at_sender=True)
        username = base_info_json["card"]["name"]
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
        msg = '\n查询UID：' + content + '的用户名失败，请检查拼写/API寄了'
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    guard_info_json = await get_user_guard(content)

    try:
        guard_len = len(guard_info_json)
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
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
        nonebot.logger.error(e)
        msg = '\n查询UID：' + content + '失败，请检查拼写/没有舰团/API寄了'
        await catch_str.finish(Message(f'{msg}'), at_sender=True)

    output = await md_to_pic(md=out_str, width=500)
    await catch_str5.send(MessageSegment.image(output))


catch_str6 = on_keyword({'/查昵称 '})


@catch_str6.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

    info_json = await get_user_keyword_info(content)
    # nonebot.logger.info(info_json)

    try:
        result = info_json['data']['result']
    except (KeyError, TypeError, IndexError) as e:
        nonebot.logger.error(e)
        msg = '\n查询无结果，请检查拼写或是接口寄了'
        await catch_str6.finish(Message(f'{msg}'), at_sender=True)

    msg = "\n 查询用户名：" + content + "\n" + \
          " 显示格式为：【 UID  昵称  粉丝数 】\n"
    for i in range(len(result)):
        msg += " 【 " + str(result[i]["mid"]) + "  " + result[i]["uname"] + "  " + str(result[i]["fans"]) + ' 】\n'
    await catch_str6.finish(Message(f'{msg}'), at_sender=True)


catch_str7 = on_keyword({'/营收 '})


@catch_str7.handle()
async def _(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    content = get_msg[4:]

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
            msg = '\n请求失败，寄了喵。\n接口返回：\n' + json.dumps(json1, indent=2, ensure_ascii=False)
            await catch_str7.finish(Message(f'{msg}'), at_sender=True)
    except (KeyError, TypeError, IndexError) as e:
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
            if income > 10000000:
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
        msg = '\n数据解析失败，寄了喵（请查日志排查问题）'
        await catch_str7.finish(Message(f'{msg}'), at_sender=True)


catch_str8 = on_command("vtb网站", aliases={"VTB网站", "Vtb网站", "vtb资源", "VTB资源"})


@catch_str8.handle()
async def _(bot: Bot, event: Event, state: T_State):
    msg = '\nVTB数据看板：https://ikaros-521.gitee.io/vtb_data_board/' \
        '\nmatsuri：https://matsuri.icu/' \
        '\ndanmaku：https://danmaku.suki.club/' \
        '\nvtbs.fun：http://www.vtbs.fun/' \
        '\nbiligank：https://biligank.com/' \
        '\n火龙榜：https://huolonglive.com/#/' \
        '\nvtbs.moe：https://vtbs.moe/' \
        '\nvup.loveava.top：https://vup.loveava.top/ranking' \
        '\nzeroroku：https://zeroroku.com/bilibili'
        
    await catch_str8.finish(Message(f'{msg}'), at_sender=True)


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

    API_URL = 'http://www.vtbs.fun:8050/rank/income?dateRange=' + date_range + '&current=1&size=' + size
    # nonebot.logger.info("API_URL=" + API_URL)
    async with aiohttp.ClientSession(headers=header1) as session:
        async with session.get(url=API_URL, headers=header1) as response:
            ret = await response.json()
    # nonebot.logger.info(ret)
    return ret


# 数据预处理 返回uid
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
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            temp["uid"] = str(result[0]["mid"])
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
        API_URL = 'https://danmaku.suki.club/api/search/user/channel?uid=' + uid
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
        API_URL = 'https://danmaku.suki.club/api/search/user/detail?uid=' + src_uid + '&target=' + tgt_uid + \
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
        API_URL = 'https://danmaku.suki.club/api/info/channel?cid=' + uid
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
        API_URL = 'https://danmaku.suki.club/api/info/live?liveid=' + live_id + '&type=' + income_type + '&uid='
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


# 时间戳转换
async def timestamp_to_date(timestamp):
    # 转换成localtime
    time_local = time.localtime(timestamp / 1000)
    # 转换成新的时间格式(精确到秒)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt  # 2021-11-09 09:46:48
