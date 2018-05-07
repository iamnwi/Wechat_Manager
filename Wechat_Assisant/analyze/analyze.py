# -*- coding:utf8 -*-
import json
import pandas as pd
import operator
import jieba
import jieba.analyse
import MySQLdb
import datetime, time, pytz
from datetime import timezone
from isoweek import Week

from Wechat_Assisant.models import *
from django_pandas.io import read_frame

sex = {0:'U', 1:'M', 2:'F'}

def t_readable(t):
        sh = pytz.timezone('Asia/Shanghai')
        dt = datetime.datetime.strptime(time.ctime(int(t)), "%a %b %d %H:%M:%S %Y")
        t_loc = sh.localize(dt)
        t_read = t_loc.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        return t_read

def read_db(weeknum):
    dfs = {}
    w = Week(datetime.datetime.now().year, weeknum)
    mon_dt = datetime.datetime.combine(w.monday(), datetime.datetime.min.time())
    sun_dt = datetime.datetime.combine(w.sunday(), datetime.datetime.max.time())
    end_dt = sun_dt + datetime.timedelta(hours=4)
    begin_stamp = mon_dt.timestamp()
    end_stamp = end_dt.timestamp()

    close_old_connections()
    qs = WechatClient.objects.all()
    dfs['user'] = read_frame(qs)
    close_old_connections()
    qs = Group.objects.all()
    dfs['group'] = read_frame(qs)
    close_old_connections()
    qs = Message.objects.filter(msg_time__range=(begin_stamp, end_stamp))
    dfs['message'] = read_frame(qs)

    return dfs

def str2json(s, fd=False, group=False):
    # friend list
    if fd:
        s = s.replace('<ContactList: []>', "[]").replace('<User: ', '').replace('}>,', '},').replace('}>]', '}]')
        s = s.replace('"', "'").replace("{'", '{"').replace(", '", ', "').replace("':", '":').replace(": '", ': "').replace("',", '",')
        s = s.replace('\\', '')
    # group list
    if group:
        s = s.replace('[<Chatroom:', '').replace('<ContactList:', '').replace('[<ChatroomMember:', '').replace('<ChatroomMember:', '')
        s= s.replace(']>', ']').replace('}>', '}')
        s = s.replace('"', "'").replace("{'", '{"').replace(", '", ', "').replace("':", '":').replace(": '", ': "').replace("',", '",')
        s = s.replace("'}", '"}')
        s = s.replace('\\', '')
    return s

def clean(fd_ls=None, group_ls=None, mp_ls=None):
    if fd_ls:
        nick_dict = {}
        for fd in fd_ls:
            if fd['NickName'] not in nick_dict:
                nick_dict[fd['NickName']] = fd
        return list(nick_dict.values())
    elif group_ls:
        return group_ls
    elif mp_ls:
        nick_dict = {}
        for mp in mp_ls:
            if mp['NickName'] not in nick_dict:
                nick_dict[mp['NickName']] = mp
        return list(nick_dict.values())

class User:
    user_dict = {}

    def __init__(self, row, mdf, gdf):
        self.openid = row['openid']
        self.uin = row['uin']
        self.nick = row['nick_name']

        if row['friend_list'] == '[]':
            self.fd_ls = []
        else:
            fd_str = str2json(row['friend_list'], fd=True) if row['friend_list'][1] == '<' else row['friend_list']
            self.fd_ls = clean(fd_ls=json.loads(fd_str))

        if row['group_list'] == '[]':
            self.group_ls = []
        else:
            self.group_ls = clean(group_ls=json.loads(row['group_list'])) if row['group_list'][1] != '<' else []

        if row['mp_list'] == '[]':
            self.mp_ls = []
        else:
            self.mp_ls = clean(mp_ls=json.loads(row['mp_list'])) if row['mp_list'][1] != '<' else []

        self.mdf = mdf[mdf['msg_uin'] == self.uin]

        self.gdf = gdf[gdf['uin'] == self.uin]

        self.analyze_dict = {}

        User.user_dict[row['openid']] = self

    def analyze(self, year, weeknum):
        self.analyze_dict['year'] = year
        self.analyze_dict['weeknum'] = weeknum
        self.analyze_dict['user_nick'] = self.nick
        # print('----------------------')
        # print('nick name:%s, openid:%s' % (self.nick, self.openid))
        self.friend_statistic()
        self.group_statistic()
        self.mp_statistic()
        self.message_statistic()
        # print('----------------------')

        # insert result into DB
        res = json.dumps(self.analyze_dict)
        # weeknum = datetime.date.today().isocalendar()[1]
        new_values = {'openid': self.openid, 'result': res, 'year': year, 'weeknum': weeknum}
        close_old_connections()
        obj, created = Analyze.objects.update_or_create(openid=self.openid, year=year, weeknum=weeknum, defaults=new_values,)
        obj.save()

    def friend_statistic(self):
        friend_ana_dict = {}
        if self.fd_ls == []:
            friend_ana_dict['total_fd'] = 0
            self.analyze_dict['friend'] = friend_ana_dict
            # print('No friend infomation')
            return

        fd_ls = self.fd_ls
        user = fd_ls[0]
        # friend_ana_dict['user_nick'] = user_nick = user['NickName']
        friend_ana_dict['user_sex'] = user_sex = sex[user['Sex']]
        user_nick = user['NickName']
        # user_sex = sex[user['Sex']]
        tot = len(fd_ls)-1
        sex_count = {}
        province_count = {}
        city_count = {}
        sex_count[0] = sex_count[1] = sex_count[2] = 0
        tot_fd = 0
        for fd in fd_ls[1:]:
            sex_count[fd['Sex']] = sex_count[fd['Sex']] + 1
            province_count[fd['Province']] = province_count[fd['Province']]+1 if fd['Province'] in province_count else 1
            city_count[fd['City']] = city_count[fd['City']]+1 if fd['City'] in city_count else 1

        # print('%s(sex:%s):' % (user_nick, user_sex))
        # print('ToT: %d' % (len(fd_ls)-1))
        friend_ana_dict['sex_cnt'] = sex_count
        sorted_p = sorted(province_count.items(), key=operator.itemgetter(1), reverse=True)
        friend_ana_dict['province_cnt'] = sorted_p
        sorted_c = sorted(city_count.items(), key=operator.itemgetter(1), reverse=True)
        friend_ana_dict['city_cnt'] = sorted_c

        # for k,v in sex_count.items():
        #     print('%s: %s, %.2lf%%' % (sex[k], v, v/tot*100))
        # for k,v in province_count.items():
        #     print('%s: %d' % (k, v))
        # for k,v in city_count.items():
        #     print('%s: %d' % (k, v))

        self.analyze_dict['friend'] = friend_ana_dict

    def group_statistic(self):
        group_ana_dict = {}
        group_ana_dict['total_group'] = len(self.group_ls)

        if self.group_ls == []:
            self.analyze_dict['group'] = group_ana_dict
            # print('No group infomation')
            return

        group_ls = self.group_ls
        # print('Group Count: %d' % len(group_ls))

        member_cnt = {}
        for group in group_ls:
            member_cnt.update({group['NickName']: group['MemberCount']})

        sorted_mcnt = sorted(member_cnt.items(), key=operator.itemgetter(1), reverse=True)
        group_ana_dict['g_member_cnt'] = sorted_mcnt
        # for nick, cnt in sorted_mcnt[:5]:
        #     print('%s: %d' % (nick, cnt))

        self.analyze_dict['group'] = group_ana_dict

    def mp_statistic(self):
        mp_ana_dict = {}
        mp_ana_dict['total_mp'] =  len(self.mp_ls)
        if self.mp_ls == []:
            self.analyze_dict['mp'] = mp_ana_dict
            # print('No MP infomation')
            return

        mp_ls = self.mp_ls
        # print('MP Count: %d' % len(mp_ls))

        keyword_cnt = {}
        for mp in mp_ls:
            keywords = jieba.analyse.extract_tags(mp['Signature'], topK=5, withWeight=True, allowPOS=())
            for word, weight in keywords:
                keyword_cnt[word] = keyword_cnt[word]+1 if word in keyword_cnt else 1

        sorted_cnt = sorted(keyword_cnt.items(), key=operator.itemgetter(1), reverse=True)
        mp_ana_dict['mp_keywrods_cnt'] = sorted_cnt
        # for k,v in sorted_cnt[:10]:
        #     print('%s: %d' % (k,v))

        self.analyze_dict['mp'] = mp_ana_dict

    def message_statistic(self):
        msg_ana_dict = {}
        msg_ana_dict['total_message'] = self.mdf.shape[0]
        # print('total message count: %d' % self.mdf.shape[0])

        if msg_ana_dict['total_message'] == 0:
            self.analyze_dict['message'] = msg_ana_dict
            # print('No message infomation')
            return

        one2one_mdf = self.mdf[(self.mdf['msg_is_group'] == False) & (self.mdf['msg_is_mp'] == False)]
        msg_ana_dict['one2one_msg'] = one2one_mdf.shape[0]
        # print('1-1 coversation message count: %d' % one2one_mdf.shape[0])

        group_mdf = self.mdf[(self.mdf['msg_is_group'] == True)]
        msg_ana_dict['g_msg_cnt'] = group_mdf.shape[0]
        # print('group message count: %d' % group_mdf.shape[0])

        mp_mdf = self.mdf[(self.mdf['msg_is_mp'] == True)]
        msg_ana_dict['mp_msg_cnt'] = mp_mdf.shape[0]
        # print('mp message count: %d' % mp_mdf.shape[0])

        msg_ana_dict['g_msg_isat_cnt'] = group_mdf[group_mdf['is_at']==True].shape[0]
        # print('group @ message count: %d' % group_mdf[group_mdf['is_at']==True].shape[0])

        sent_mdf = self.mdf[(self.mdf['send'] == True)]
        msg_ana_dict['sent_msg_cnt'] = sent_mdf.shape[0]
        # print('sent message count: %d' % sent_mdf.shape[0])

        self.mdf.sort_values(by=['msg_time'])
        msg_day_count = [0] * 7
        g_msg_day_count = [0] * 7
        one2one_msg_day_count = [0] * 7
        mp_msg_day_count = [0] * 7
        latest_time = [0] * 7
        for index, row in self.mdf.iterrows():
            showntime = datetime.datetime.strptime(time.ctime(int(row['msg_time'])), "%a %b %d %H:%M:%S %Y")
            msg_day_count[showntime.weekday()] += 1
            if row['msg_is_group']:
                g_msg_day_count[showntime.weekday()] += 1
            elif row['msg_is_mp']:
                mp_msg_day_count[showntime.weekday()] += 1
            else:
                one2one_msg_day_count[showntime.weekday()] += 1

            midnight4am = showntime.replace(hour=4, minute=0, second=0, microsecond=0)
            # if midnight1am < showntime and midnight4am > showntime:
            wday = showntime.weekday() if midnight4am < showntime or showntime.weekday() == 0 else showntime.weekday()-1
            # showntime.astimezone(pytz.timezone('Asia/Shanghai'))
            # latest_time[wday] = showntime.replace(tzinfo=timezone.utc).timestamp()
            # latest_time[wday] = showntime.timestamp()
            latest_time[wday] = row['msg_time']

        # print(latest)
        # print('-------messages per day-------')
        msg_ana_dict['msg_per_wday_ls'] = msg_day_count
        msg_ana_dict['g_msg_per_wday_ls'] = g_msg_day_count
        msg_ana_dict['mp_msg_per_wday_ls'] = mp_msg_day_count
        msg_ana_dict['one2one_msg_per_wday_ls'] = one2one_msg_day_count
        # wday = 1
        # for cnt in msg_day_count:
        #     if cnt:
        #         print('weekday %d: %d' % (wday, cnt))
        #     wday += 1
        # print('-------latest msg per day-------')
        msg_ana_dict['latest_msg_per_wday_ls'] = latest_time
        # wday = 1
        # for cnt in latest_time:
            # if cnt:
            #     print('weekday %d: %s' % (wday, time.ctime(cnt)))
            # else:
            #     print('weekday %d: %s' % (wday, 'no record'))
            # wday += 1

        g_msg_cnt = {}
        for index, row in group_mdf.iterrows():
            g_name = row['group_name']
            selected_df = self.gdf[self.gdf['name']==g_name]
            if selected_df.shape[0] > 0:
                g_nick = selected_df.iloc[0]['nick_name']
                g_msg_cnt[g_nick] = g_msg_cnt[g_nick]+1 if g_nick in g_msg_cnt else 1
        sorted_cnt = sorted(g_msg_cnt.items(), key=operator.itemgetter(1), reverse=True)
        msg_ana_dict['g_msg_per_group'] = sorted_cnt
        # print('-------group msg per group-------')
        # for k,v in sorted_cnt:
        #     print('%s: %d' % (k, v))

        self.analyze_dict['message'] = msg_ana_dict

    @staticmethod
    def batch_create(udf, mdf, gdf):
        for index, row in udf.iterrows():
            User(row, mdf, gdf)

    @staticmethod
    def batch_analyze(openid=None, year=None, week=None):
        ana_ls = []
        if openid:
            ana_ls.append(User.user_dict[openid])
        else:
            ana_ls = list(User.user_dict.values())

        for user in ana_ls:
            user.analyze(year, week)

def analyze():
    while True:
        today = datetime.datetime.today()
        weekday = today.weekday()

        # do it on Monday(weekday == 0)
        if weekday == 0 and today.hour >= 6:
            start_delta = datetime.timedelta(days=weekday, weeks=1)
            start_of_week = today - start_delta
            weeknum = start_of_week.isocalendar()[1]
            year = start_of_week.isocalendar()[0]
            dfs = read_db(weeknum)

            User.batch_create(dfs['user'], dfs['message'], dfs['group'])
            User.batch_analyze(year=year, week=weeknum)
            User.user_dict.clear()

        time.sleep(3600*24)
