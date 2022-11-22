# import datetime
import nonebot
import requests
import time
# from io import BytesIO
from nonebot import on_keyword
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

'''
私人bot项目地址：https://github.com/Ikaros-521/LX_Bot
本插件项目地址：https://github.com/Ikaros-521/nonebot_plugin_searchBiliInfo

插件依赖：requests，nonebot_plugin_htmlrender

插件功能：
/查 昵称关键词或uid(uid需要以:或：或uid:或UID:打头)
/查直播 昵称关键词或uid 场次数（默认不写为全部）
/查舰团 昵称关键词或uid
/查昵称 昵称关键词或uid
/查收益 昵称关键词或uid 收益类型(默认1: 礼物，2: 上舰，3: SC) 倒叙第n场(从0开始)
/查成分 观看 昵称关键词或uid
/查成分 弹幕 查询的目标人昵称关键词或uid 查询的主播昵称关键词或uid 页数 条数
'''

# 请求头贴入你的b站cookie
header1 = {
    'cookie': 'buvid3=52D30BB7-20FB-C7BA-60B7-EB3F18A8EB9C62437infoc; b_nut=1662632862; i-wanna-go-back=-1; b_ut=5; '
              '_uuid=FB5921023-4BF10-D48E-10A62-EE619E5FA65E60948infoc; buvid_fp=3b2946a9aa52740147f7478c79476df7; '
              'buvid4=0068E57C-9762-7898-4F73-0B8994558CF463776-022090818-FRmBv7s/ltnMkEnT97AnUQ%3D%3D; '
              'fingerprint=eac7b07cd79cd55526b5a7206425ddc6; buvid_fp_plain=undefined; '
              'SESSDATA=89e822a8%2C1678184893%2Cb9824%2A91; bili_jct=3d33d52161227b9ec082ba6124be8d63; '
              'DedeUserID=1123180192; DedeUserID__ckMd5=6b55cc0fe28987d3; sid=8m93076x; PVID=25; '
              'LIVE_BUVID=AUTO9316626329021634; Hm_lvt_8a6e55dbd2870f0f5bc9194cddf32a02=1663557853,1663637087,'
              '1663811728,1663935967; bp_video_offset_1123180192=707172485766840300; b_lsid=338EE34E_1836A5BC399; '
              '_dfcaptcha=62ba3e19085f0e3de59bc4dcf7663756; innersign=0; '
              'Hm_lpvt_8a6e55dbd2870f0f5bc9194cddf32a02=1663937476 '
}


catch_str = on_keyword({'/查 '})
@catch_str.handle()
async def send_msg(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    id = event.get_user_id()
    # nonebot.logger.info(get_msg)
    content = get_msg[3:]

    content = data_preprocess(content)
    # uid检索完成的标志位
    flag = 0

    # 遍历本地DATA
    for i in range(len(DATA)):
        # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
        try:
            if content == DATA[i]["uname"]:
                content = str(DATA[i]["mid"])
                flag = 1
                break
        except (KeyError, TypeError, IndexError) as e:
            continue

    # 本地没有匹配到，则从b站搜索
    if flag != 1:
        # 通过昵称查询uid，默认只查搜索到的第一个用户
        info_json = await use_name_get_uid(content)
        # nonebot.logger.info(info_json)

        try:
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            content = str(result[0]["mid"])
        except (KeyError, TypeError, IndexError) as e:
            nonebot.logger.info("查询不到用户名为：" + content + " 的相关信息")

    # 传入uid获取用户基本信息
    base_info_json = await get_base_info(content)
    # 获取用户信息失败
    if base_info_json['code'] != 0:
        msg = "[CQ:at,qq={}]".format(id) + '\n获取uid：' + content + '，用户信息失败'
        await catch_str.finish(Message(f'{msg}'))
        return
    # 获取用户直播间id
    room_id = await get_room_id(content)
    # 没有直播间 默认为0
    if room_id == 0:
        guard_info_json = {"data": {"info": {"num": 0}}}
    else:
        guard_info_json = await get_guard_info(content, room_id)

    msg = "[CQ:at,qq={}]".format(id) + '\n用户名：' + base_info_json['card']['name'] + '\nUID：' + str(base_info_json['card']['mid']) + \
          '\n房间号：' + str(room_id) + '\n粉丝数：' + str(base_info_json['card']['fans']) + '\n舰团数：' + str(guard_info_json['data']['info']['num'])
    await catch_str.finish(Message(f'{msg}'))


catch_str1 = on_keyword({'/查成分 弹幕 '})
@catch_str1.handle()
async def send_msg(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[8:]

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
        id = event.get_user_id()
        msg = "[CQ:at,qq={}]".format(id) + '传参错误，命令格式【/查成分 弹幕 用户uid 目标uid 页数】'
        await catch_str1.finish(Message(f'{msg}'))
        return

    if len(content) == 3:
        page = content[2]

    content = data_preprocess(content)
    # uid检索完成的标志位
    flag = 0

    # 遍历本地DATA
    for i in range(len(DATA)):
        # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
        try:
            if src_uid == DATA[i]["uname"]:
                src_uid = str(DATA[i]["mid"])
                flag = 1
                break
        except (KeyError, TypeError, IndexError) as e:
            continue

    # 本地没有匹配到，则从b站搜索
    if flag != 1:
        # 通过昵称查询uid，默认只查搜索到的第一个用户
        info_json = await use_name_get_uid(src_uid)
        # nonebot.logger.info(info_json)

        try:
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            src_uid = str(result[0]["mid"])
        except (KeyError, TypeError, IndexError) as e:
            nonebot.logger.info("查询不到用户名为：" + src_uid + " 的相关信息")

    # 由于逻辑问题 查uid时需要追加uid在命令后
    if not tgt_uid.startswith("uid"):
        # uid检索完成的标志位
        flag = 0

        # 遍历本地DATA
        for i in range(len(DATA)):
            # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
            try:
                if tgt_uid == DATA[i]["uname"]:
                    tgt_uid = str(DATA[i]["mid"])
                    flag = 1
                    break
            except (KeyError, TypeError, IndexError) as e:
                continue

        # 本地没有匹配到，则从b站搜索
        if flag != 1:
            # 通过昵称查询uid，默认只查搜索到的第一个用户
            info_json = await use_name_get_uid(tgt_uid)
            # nonebot.logger.info(info_json)

            try:
                result = info_json['data']['result']
                # 只获取第一个搜索结果的数据
                tgt_uid = str(result[0]["mid"])
            except (KeyError, TypeError, IndexError) as e:
                nonebot.logger.info("查询不到用户名为：" + tgt_uid + " 的相关信息")
    else:
        tgt_uid = tgt_uid[3:]

    info_json = await get_detail_info(src_uid, tgt_uid, page, page_size)

    try:
        # 判断返回代码
        if info_json['code'] != 200:
            id = event.get_user_id()
            msg = "[CQ:at,qq={}]".format(id) + '查询出错'
            await catch_str1.finish(Message(f'{msg}'))
            return
    except (KeyError, TypeError, IndexError) as e:
        msg = "[CQ:at,qq={}]".format(id) + '果咩，查询信息失败喵~请检查拼写'
        await catch_str1.finish(Message(f'{msg}'))

    data_len = 0
    out_str = "#查成分 弹幕\n\n查询用户UID:" + src_uid + ", 目标UID:" + tgt_uid + ", 页数:" + page + ", 条数:" + page_size + "\n\n" + \
              "| 时间 | 内容 |\n" \
              "| :-----| :-----|\n"
    for i in range(len(info_json['data']['data'])):
        title = info_json['data']['data'][i]['live']['title']
        out_str += '| 标题 | ' + title + ' |\n'
        for j in range(len(info_json['data']['data'][i]['danmakus'])):
            date = await timestamp_to_date(info_json['data']['data'][i]['danmakus'][j]['sendDate'])
            message = info_json['data']['data'][i]['danmakus'][j]['message']
            out_str += '| ' + str(date) + '| ' + message + '|\n'
            data_len += 1
        out_str += '| -- | -- |\n'
    # nonebot.logger.info("\n" + out_str)

    if data_len < 1000:
        output = await md_to_pic(md=out_str, width=1000)
        await catch_str1.send(MessageSegment.image(output))
    else:
        id = event.get_user_id()
        msg = "[CQ:at,qq={}]".format(id) + '果咩，弹幕数大于1000，发不出去喵~'
        await catch_str1.finish(Message(f'{msg}'))


catch_str2 = on_keyword({'/查成分 观看 '})
@catch_str2.handle()
async def send_msg2(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[8:]
    id = event.get_user_id()

    content = data_preprocess(content)
    # uid检索完成的标志位
    flag = 0

    # 遍历本地DATA
    for i in range(len(DATA)):
        # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
        try:
            if content == DATA[i]["uname"]:
                content = str(DATA[i]["mid"])
                flag = 1
                break
        except (KeyError, TypeError, IndexError) as e:
            continue

    # 本地没有匹配到，则从b站搜索
    if flag != 1:
        # 通过昵称查询uid，默认只查搜索到的第一个用户
        info_json = await use_name_get_uid(content)
        # nonebot.logger.info(info_json)

        try:
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            content = str(result[0]["mid"])
        except (KeyError, TypeError, IndexError) as e:
            nonebot.logger.info("查询不到用户名为：" + content + " 的相关信息")

    user_info_json = await get_user_info(content)

    try:
        # 判断返回代码
        if user_info_json['code'] != 200:
            msg = "[CQ:at,qq={}]".format(id) + '查询用户：' + content + '失败'
            await catch_str2.finish(Message(f'{msg}'))
            return
    except (KeyError, TypeError, IndexError) as e:
        msg = "[CQ:at,qq={}]".format(id) + '果咩，查询用户信息失败喵~请检查拼写'
        await catch_str2.finish(Message(f'{msg}'))

    out_str = "#查观看\n\n查询用户UID：" + content + "\n\n" + \
              "| 昵称 | UID | 房间号 |\n"\
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

    out_str += " 观看总数：" + str(len(uId_set)) + "\n"

    for i in range(len(uId_set)):
        out_str += "| {:<s} | {:<d} | {:<d} |".format(name_list[i], uId_list[i], roomId_list[i])
        out_str += '\n'
    # nonebot.logger.info("\n" + out_str)

    if len(uId_set) < 1000:
        output = await md_to_pic(md=out_str, width=500)
        await catch_str2.send(MessageSegment.image(output))
    else:
        msg = "[CQ:at,qq={}]".format(id) + '果咩，dd数大于1000，发不出去喵~'
        await catch_str2.finish(Message(f'{msg}'))


catch_str3 = on_keyword({'/查直播 '})
@catch_str3.handle()
async def send_msg3(bot: Bot, event: Event, state: T_State):
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
        msg = "[CQ:at,qq={}]".format(id) + '传参错误，命令格式【/查直播 用户uid 最近场次数】'
        await catch_str3.finish(Message(f'{msg}'))
        return

    src_uid = data_preprocess(src_uid)
    # uid检索完成的标志位
    flag = 0

    # 遍历本地DATA
    for i in range(len(DATA)):
        # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
        try:
            if src_uid == DATA[i]["uname"]:
                src_uid = str(DATA[i]["mid"])
                flag = 1
                break
        except (KeyError, TypeError, IndexError) as e:
            continue

    # 本地没有匹配到，则从b站搜索
    if flag != 1:
        # 通过昵称查询uid，默认只查搜索到的第一个用户
        info_json = await use_name_get_uid(src_uid)
        # nonebot.logger.info(info_json)

        try:
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            src_uid = str(result[0]["mid"])
        except (KeyError, TypeError, IndexError) as e:
            nonebot.logger.info("查询不到用户名为：" + src_uid + " 的相关信息")

    info_json = await get_info(src_uid)

    # 判断返回代码
    if info_json['code'] != 200:
        msg = "[CQ:at,qq={}]".format(id) + '查询用户：' + src_uid + '失败'
        await catch_str3.finish(Message(f'{msg}'))
        return

    out_str = "#查直播\n\n昵称:" + info_json["data"]["channel"]["name"] + "  UID:" + src_uid + "  房间号:" + \
              str(info_json["data"]["channel"]["roomId"]) + "\n\n 总直播数:" + \
              str(info_json["data"]["channel"]["totalLiveCount"]) + \
              "  总弹幕数:" + str(info_json["data"]["channel"]["totalDanmakuCount"]) + "  总收益:￥" + \
              str(info_json["data"]["channel"]["totalIncome"]) + \
              "  总直播时长:" + str(round(info_json["data"]["channel"]["totalLiveSecond"] / 60 / 60, 2)) + "h\n\n" + \
              "| 开始时间 | 时长 | 标题 | 弹幕数 | 观看数 | 互动数 | 总收益 |\n" \
              "| :-----| :-----| :-----| :-----| :-----| :-----| :-----|\n"

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
                    (info_json["data"]["lives"][i]["stopDate"] - info_json["data"]["lives"][i]["startDate"]) / 1000 / 3600,
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
    # nonebot.logger.info("\n" + out_str)

    if len(info_json["data"]["lives"]) < 2000:
        output = await md_to_pic(md=out_str, width=1000)
        await catch_str3.send(MessageSegment.image(output))
    else:
        id = event.get_user_id()
        msg = "[CQ:at,qq={}]".format(id) + '果咩，直播数大于2000，发不出去喵~'
        await catch_str3.finish(Message(f'{msg}'))


catch_str4 = on_keyword({'/查收益 '})
@catch_str4.handle()
async def send_msg4(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    id = event.get_user_id()
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
        msg = "[CQ:at,qq={}]".format(id) + '传参错误，命令格式【/查直播 收益类型(默认1: 礼物，2: 上舰，3: SC) 用户uid 倒叙第n场(从0开始)】'
        await catch_str4.finish(Message(f'{msg}'))
        return

    src_uid = data_preprocess(src_uid)
    # uid检索完成的标志位
    flag = 0

    # 遍历本地DATA
    for i in range(len(DATA)):
        # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
        try:
            if src_uid == DATA[i]["uname"]:
                src_uid = str(DATA[i]["mid"])
                flag = 1
                break
        except (KeyError, TypeError, IndexError) as e:
            continue

    # 本地没有匹配到，则从b站搜索
    if flag != 1:
        # 通过昵称查询uid，默认只查搜索到的第一个用户
        info_json = await use_name_get_uid(src_uid)
        # nonebot.logger.info(info_json)

        try:
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            src_uid = str(result[0]["mid"])
        except (KeyError, TypeError, IndexError) as e:
            nonebot.logger.info("查询不到用户名为：" + src_uid + " 的相关信息")

    live_json = await get_info(src_uid)

    # 判断返回代码
    if live_json['code'] != 200:
        msg = "[CQ:at,qq={}]".format(id) + '查询用户：' + src_uid + ' 直播信息失败'
        await catch_str4.finish(Message(f'{msg}'))
        return

    try:
        live_id = live_json['data']['lives'][int(live_index)]['liveId']
        username = live_json["data"]["channel"]["name"]
        room_id = str(live_json["data"]["channel"]["roomId"])
        totalLiveCount = str(live_json["data"]["channel"]["totalLiveCount"])
        totalDanmakuCount = str(live_json["data"]["channel"]["totalDanmakuCount"])
        totalIncome = str(live_json["data"]["channel"]["totalIncome"])
        totalLivehour = str(round(live_json["data"]["channel"]["totalLiveSecond"] / 60 / 60, 2))
    except (KeyError, TypeError, IndexError) as e:
        msg = "[CQ:at,qq={}]".format(id) + '查询用户：' + src_uid + '失败,live_id解析失败,可能原因：场次数不对；无此场次'
        await catch_str4.finish(Message(f'{msg}'))
        return

    out_str = "#查收益\n\n昵称:" + username + "  UID:" + src_uid + "  房间号:" + room_id + "\n\n 总直播数:" + \
              totalLiveCount + "  总弹幕数:" + totalDanmakuCount + "  总收益:￥" + totalIncome + \
              "  总直播时长:" + totalLivehour + "h\n\n" + \
              "| 时间 | uid | 昵称 | 内容 | 价格|\n" \
              "| :-----| :-----| :-----| :-----| :-----|\n"

    # 默认1: 礼物，2: 上舰，3: SC
    if income_type == "礼物":
        income_type = "1"
    elif income_type == "上舰":
        income_type = "2"
    elif income_type == "SC" or income_type == "sc" or income_type == "Sc":
        income_type = "3"
    else:
        income_type = "1"

    # nonebot.logger.info(out_str + "income_type:" + income_type)

    # 获取当场直播信息
    info_json = await get_live_info(live_id, income_type)
    if info_json['code'] != 200:
        msg = "[CQ:at,qq={}]".format(id) + '查询用户：' + src_uid + ' 场次数据失败'
        await catch_str4.finish(Message(f'{msg}'))
        return

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
    # nonebot.logger.info("\n" + out_str)

    if len(info_json["data"]["danmakus"]) < 2000:
        output = await md_to_pic(md=out_str, width=1000)
        await catch_str4.send(MessageSegment.image(output))
    else:
        id = event.get_user_id()
        msg = "[CQ:at,qq={}]".format(id) + '果咩，礼物数大于2000，发不出去喵~'
        await catch_str4.finish(Message(f'{msg}'))


catch_str5 = on_keyword({'/查舰团 '})
@catch_str5.handle()
async def send_img(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

    username = ""

    content = data_preprocess(content)
    # uid检索完成的标志位
    flag = 0

    # 遍历本地DATA
    for i in range(len(DATA)):
        # 本地匹配到结果 就直接使用本地的(由于DATA源自https://api.vtbs.moe/v1/short，可能有空数据，需要异常处理下）
        try:
            if content == DATA[i]["uname"]:
                username = DATA[i]["uname"]
                content = str(DATA[i]["mid"])
                flag = 1
                break
        except (KeyError, TypeError, IndexError) as e:
            continue

    # 本地没有匹配到，则从b站搜索
    if flag != 1:
        # 通过昵称查询uid，默认只查搜索到的第一个用户
        info_json = await use_name_get_uid(content)
        # nonebot.logger.info(info_json)

        try:
            result = info_json['data']['result']
            # 只获取第一个搜索结果的数据
            content = str(result[0]["mid"])
            username = result[i]["uname"]
        except (KeyError, TypeError, IndexError) as e:
            nonebot.logger.info("查询不到用户名为：" + content + " 的相关信息")

    guard_info_json = await get_user_guard(content)

    out_str = "#查舰团\n\n查询用户名：" + username + "  UID：" + content + "\n\n" + \
              "| 昵称 | UID | 舰团类型 |\n" \
              "| :-----| :-----| :-----|\n"
    for i in range(len(guard_info_json)):
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
    # nonebot.logger.info("\n" + out_str)

    output = await md_to_pic(md=out_str, width=500)
    await catch_str5.send(MessageSegment.image(output))


catch_str6 = on_keyword({'/查昵称 '})
@catch_str6.handle()
async def send_msg(bot: Bot, event: Event, state: T_State):
    get_msg = str(event.get_message())
    # nonebot.logger.info(get_msg)
    content = get_msg[5:]

    info_json = await get_user_keyword_info(content)
    # nonebot.logger.info(info_json)
    id = event.get_user_id()

    try:
        result = info_json['data']['result']
    except KeyError:
        msg = "[CQ:at,qq={}]".format(id) + ' 查询无结果'
        await catch_str6.finish(Message(f'{msg}'))
        return

    msg = "[CQ:at,qq={}]".format(id) + "\n 查询用户名：" + content + "\n" + \
          " 显示格式为：【 UID  昵称  粉丝数 】\n"
    for i in range(len(result)):
        msg += " 【 " + str(result[i]["mid"]) + "  " + result[i]["uname"] + "  " + str(result[i]["fans"]) + ' 】\n'
    await catch_str6.finish(Message(f'{msg}'))


# 数据预处理
def data_preprocess(content):
    # 由于逻辑问题 查uid时需要追加(以:或：或uid:或UID:打头)在命令后
    if content.startswith("uid:") or content.startswith("UID:"):
        content = content[4:]
    elif content.startswith(":") or content.startswith("："):
        content = content[1:]
    else:
        return content
    return content


# 传入uid获取用户基本信息
async def get_base_info(uid):
    API_URL = 'https://account.bilibili.com/api/member/getCardByMid?mid=' + uid
    ret = requests.get(API_URL)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


# 传入uid获取用户直播间房间号
async def get_room_id(uid):
    API_URL = 'https://api.live.bilibili.com/room/v2/Room/room_id_by_uid?uid=' + uid
    ret = requests.get(API_URL)
    ret = ret.json()
    try:
        room_id = ret['data']['room_id']
    except TypeError:
        return 0
    return room_id


# 获取舰团信息
async def get_guard_info(uid, room_id):
    API_URL = 'https://api.live.bilibili.com/xlive/app-room/v2/guardTab/topList?roomid=' + str(room_id) + '&page=1&ruid=' + uid + '&page_size=0'
    ret = requests.get(API_URL)
    ret = ret.json()
    return ret


async def get_user_keyword_info(name):
    API_URL = 'https://api.bilibili.com/x/web-interface/search/type?page_size=10&keyword=' + name + \
              '&search_type=bili_user'
    ret = requests.get(API_URL, headers=header1)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


async def get_user_guard(uid):
    API_URL = 'https://api.tokyo.vtbs.moe/v1/guard/' + uid
    ret = requests.get(API_URL)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret

async def get_user_info(uid):
    API_URL = 'https://danmaku.suki.club/api/search/user/channel?uid=' + uid
    ret = requests.get(API_URL, verify=False)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


async def get_detail_info(src_uid, tgt_uid, page, page_size):
    API_URL = 'https://danmaku.suki.club/api/search/user/detail?uid=' + src_uid + '&target=' + tgt_uid + \
              '&pagenum=' + page + '&pagesize=' + page_size
    ret = requests.get(API_URL, verify=False)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


async def get_info(uid):
    API_URL = 'https://danmaku.suki.club/api/info/channel?cid=' + uid
    ret = requests.get(API_URL, verify=False)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


async def get_live_info(live_id, income_type):
    API_URL = 'https://danmaku.suki.club/api/info/live?liveid=' + live_id + '&type=' + income_type + '&uid='
    ret = requests.get(API_URL, verify=False)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


# 通过昵称查询信息
async def use_name_get_uid(name):
    API_URL = 'https://api.bilibili.com/x/web-interface/search/type?page_size=10&keyword=' + name + \
              '&search_type=bili_user'
    ret = requests.get(API_URL, headers=header1)
    ret = ret.json()
    # nonebot.logger.info(ret)
    return ret


async def timestamp_to_date(timestamp):
    # 转换成localtime
    time_local = time.localtime(timestamp / 1000)
    # 转换成新的时间格式(精确到秒)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt  # 2021-11-09 09:46:48

