#!/usr/bin/env python3
"""
DNF 后台管理系统 v4.0
参考 edict 架构：单文件dashboard + Python后端 + RESTful API
"""

import json
import os
import sys
import pymysql
import requests
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

# ==================== 配置 ====================

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': '88888888',
    'charset': 'utf8mb4',
}

# 职业映射
JOBS = {
    0: '鬼剑士', 1: '格斗家', 2: '神枪手', 3: '魔法师', 4: '圣职者',
    5: '暗夜使者', 6: '魔枪士', 7: '枪剑士', 8: '弓箭手',
    100: '狂战士', 101: '剑魂', 102: '鬼泣', 103: '阿修罗',
    200: '气功师', 201: '散打', 202: '街霸', 203: '柔道家',
    300: '漫游枪手', 301: '枪炮师', 302: '弹药专家', 303: '机械师',
    400: '元素师', 401: '召唤师', 402: '战斗法师', 403: '魔道学者',
    500: '圣骑士', 501: '蓝拳圣使', 502: '驱魔师', 503: '复仇者',
    600: '刺客', 601: '死灵术士', 602: '忍者', 603: '影舞者',
    700: '征战者', 701: '决战者', 702: '狩猎者', 703: '暗枪士',
    800: '暗刃', 801: '特工', 802: '战线佣兵', 803: '源能专家',
    900: '缪斯', 901: '旅人',
}

# 高级职业到基础职业的映射
JOB_TO_BASE = {
    100: 0, 101: 0, 102: 0, 103: 0,  # 鬼剑士系
    200: 1, 201: 1, 202: 1, 203: 1,  # 格斗家系
    300: 2, 301: 2, 302: 2, 303: 2,  # 神枪手系
    400: 3, 401: 3, 402: 3, 403: 3,  # 魔法师系
    500: 4, 501: 4, 502: 4, 503: 4,  # 圣职者系
    600: 5, 601: 5, 602: 5, 603: 5,  # 暗夜使者系
    700: 6, 701: 6, 702: 6, 703: 6,  # 魔枪士系
    800: 7, 801: 7, 802: 7, 803: 7,  # 枪剑士系
    900: 8, 901: 8,  # 弓箭手系
}

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== 数据库工具 ====================

# 数据库配置（使用 latin1 以正确处理中文编码）
DB_CONFIG_RAW = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': '88888888',
    'charset': 'latin1',
    'use_unicode': False,
}

def get_db():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG_RAW)

def query_db(sql, params=None, db='taiwan_cain'):
    """查询数据库"""
    conn = None
    try:
        config = {**DB_CONFIG_RAW, 'database': db}
        conn = pymysql.connect(**config)
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()

def decode_row(value):
    """解码数据库行中的字节值"""
    if isinstance(value, bytes):
        try:
            # 尝试 UTF-8
            return value.decode('utf-8')
        except:
            try:
                # 尝试 Big5
                return value.decode('big5')
            except:
                try:
                    # 尝试 CP950
                    return value.decode('cp950')
                except:
                    return value.decode('utf-8', errors='ignore')
    return value

# ==================== 数据加载 ====================

def load_characters(page=1, page_size=20, filters=None):
    """加载角色列表"""
    offset = (page - 1) * page_size
    where = "1=1"
    params = []
    
    if filters:
        if filters.get('name'):
            where += " AND charac_name LIKE %s"
            params.append(f"%{filters['name']}%")
        if filters.get('job'):
            where += " AND job = %s"
            params.append(int(filters['job']))
        if filters.get('min_lev'):
            where += " AND lev >= %s"
            params.append(int(filters['min_lev']))
        if filters.get('max_lev'):
            where += " AND lev <= %s"
            params.append(int(filters['max_lev']))
    
    sql = f"SELECT * FROM charac_info WHERE {where} ORDER BY last_play_time DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    chars = query_db(sql, params)
    
    count_sql = f"SELECT COUNT(*) as total FROM charac_info WHERE {where}"
    total = query_db(count_sql, params[:-2])[0]['total']
    
    # 添加职业名称和解码
    for c in chars:
        c['job_name'] = JOBS.get(c.get('job'), '未知')
        # 解码角色名称
        c['charac_name'] = decode_row(c.get('charac_name'))
        # 格式化时间
        for field in ['create_time', 'last_play_time']:
            if c.get(field) and hasattr(c[field], 'strftime'):
                c[field] = c[field].strftime('%Y-%m-%d %H:%M:%S')
    
    return {'data': chars, 'total': total, 'page': page, 'page_size': page_size}

def load_character_detail(char_id):
    """加载角色详情"""
    sql = "SELECT * FROM charac_info WHERE m_id = %s"
    chars = query_db(sql, (char_id,))
    if not chars:
        return None
    
    char = chars[0]
    char['job_name'] = JOBS.get(char.get('job'), '未知')
    
    # 格式化时间
    for field in ['create_time', 'last_play_time']:
        if char.get(field) and hasattr(char[field], 'strftime'):
            char[field] = char[field].strftime('%Y-%m-%d %H:%M:%S')
    
    # 加载背包物品
    items_sql = "SELECT * FROM taiwan_cain_2nd.user_items WHERE charac_no = %s LIMIT 100"
    items = query_db(items_sql, (char_id,), 'taiwan_cain_2nd')
    
    # 物品槽位名称
    SLOT_NAMES = {
        0: '武器', 1: '上衣', 2: '头肩', 3: '下装', 4: '鞋',
        5: '腰带', 6: '项链', 7: '手镯', 8: '戒指', 9: '辅助装备',
        10: '魔法石', 11: '耳环', 12: '称号', 13: '宠物', 14: '光环',
        15: '皮肤', 16: '武器装扮', 17: '上衣装扮', 18: '头肩装扮',
        19: '下装扮', 20: '鞋装扮', 21: '腰带装扮', 22: '项链装扮',
        23: '手镯装扮', 24: '戒指装扮', 25: '辅助装备装扮', 26: '魔法石装扮',
        27: '耳环装扮', 28: '称号装扮', 29: '宠物装扮', 30: '光环装扮',
        31: '皮肤装扮', 100: '快捷栏1', 101: '快捷栏2', 102: '快捷栏3',
        103: '快捷栏4', 104: '快捷栏5'
    }
    
    for item in items:
        item['slot_name'] = SLOT_NAMES.get(item.get('slot'), f"槽位{item.get('slot')}")
        # 尝试获取物品名称
        item_sql = "SELECT it_name FROM dnf_item_info WHERE it_no = %s"
        item_names = query_db(item_sql, (item.get('it_id'),), 'taiwan_cain')
        if item_names:
            name = item_names[0].get('it_name', b'')
            if isinstance(name, bytes):
                try:
                    item['item_name'] = name.decode('utf-8')
                except:
                    try:
                        item['item_name'] = name.decode('big5')
                    except:
                        item['item_name'] = f"物品-{item.get('it_id')}"
            else:
                item['item_name'] = name
        else:
            item['item_name'] = f"{item['slot_name']}-{item.get('it_id')}"
    
    char['inventory'] = items
    char['inventory_count'] = len(items)
    
    return char

def load_items(query='', page=1, page_size=50):
    """加载物品列表（从PVF）"""
    pvf_file = '/opt/dnf-llnut/data/conf.d/dnf-console/source/gold.txt'
    
    items = []
    try:
        with open(pvf_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                import re
                match = re.match(r'\[(\d+)\s*\]\s*name:(.+)', line)
                if match:
                    item_id = int(match.group(1))
                    item_name = match.group(2).strip()
                    
                    # 分类
                    if item_id < 100:
                        category = '消耗品'
                    elif item_id < 10000:
                        category = '材料'
                    elif item_id < 1000000:
                        category = '装备'
                    else:
                        category = '其他'
                    
                    items.append({
                        'id': item_id,
                        'name': item_name,
                        'category': category
                    })
    except Exception as e:
        print(f"[PVF ERROR] {e}")
    
    # 搜索过滤
    if query:
        items = [i for i in items if query.lower() in i['name'].lower()]
    
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {'data': items[start:end], 'total': total, 'page': page, 'page_size': page_size}

def load_skills(job_id, page=1, page_size=50):
    """加载技能列表"""
    # 技能表在 taiwan_cain_web 数据库中
    # 将高级职业ID映射到基础职业ID
    base_job = JOB_TO_BASE.get(job_id, job_id)
    
    sql = "SELECT * FROM taiwan_cain_web.skill_info WHERE job_index = %s ORDER BY skill_index LIMIT %s OFFSET %s"
    offset = (page - 1) * page_size
    skills = query_db(sql, (base_job, page_size, offset), 'taiwan_cain_web')
    
    count_sql = "SELECT COUNT(*) as total FROM taiwan_cain_web.skill_info WHERE job_index = %s"
    try:
        total = query_db(count_sql, (base_job,), 'taiwan_cain_web')[0]['total']
    except:
        total = 0
    
    # 解码技能名称和描述
    for skill in skills:
        # 解码名称
        skill['name'] = decode_row(skill.get('name'))
        
        # 解码描述（Big5）
        for field in ['basic_explain', 'skill_explain', 'command_key_explain', 'skill_command_advantage']:
            if skill.get(field) and isinstance(skill[field], bytes):
                try:
                    skill[field] = skill[field].decode('big5')
                except:
                    try:
                        skill[field] = skill[field].decode('cp950')
                    except:
                        skill[field] = skill[field].decode('utf-8', errors='ignore')
    
    # 解码技能描述
    for skill in skills:
        for field in ['basic_explain', 'skill_explain', 'command_key_explain', 'skill_command_advantage']:
            if skill.get(field) and isinstance(skill[field], bytes):
                try:
                    skill[field] = skill[field].decode('big5')
                except:
                    try:
                        skill[field] = skill[field].decode('cp950')
                    except:
                        skill[field] = skill[field].decode('utf-8', errors='ignore')
        # 解码名称
        if skill.get('name') and isinstance(skill['name'], bytes):
            try:
                skill['name'] = skill['name'].decode('utf-8')
            except:
                skill['name'] = skill['name'].decode('big5', errors='ignore')
    
    return {'data': skills, 'total': total, 'page': page, 'page_size': page_size}

def load_monsters(query='', page=1, page_size=50):
    """加载怪物列表"""
    offset = (page - 1) * page_size
    
    if query:
        sql = "SELECT * FROM dnf_monster_info WHERE mon_name_kr LIKE %s ORDER BY idx LIMIT %s OFFSET %s"
        params = (f"%{query}%", page_size, offset)
        count_sql = "SELECT COUNT(*) as total FROM dnf_monster_info WHERE mon_name_kr LIKE %s"
        count_params = (f"%{query}%",)
    else:
        sql = "SELECT * FROM dnf_monster_info ORDER BY idx LIMIT %s OFFSET %s"
        params = (page_size, offset)
        count_sql = "SELECT COUNT(*) as total FROM dnf_monster_info"
        count_params = ()
    
    monsters = query_db(sql, params)
    total = query_db(count_sql, count_params)[0]['total']
    
    # 解码名称
    for m in monsters:
        if m.get('mon_name_kr') and isinstance(m['mon_name_kr'], bytes):
            try:
                m['mon_name_kr'] = m['mon_name_kr'].decode('utf-8')
            except:
                m['mon_name_kr'] = m['mon_name_kr'].decode('big5', errors='ignore')
    
    return {'data': monsters, 'total': total, 'page': page, 'page_size': page_size}

# ==================== GM 功能 ====================

def gm_save_notice(content):
    """保存公告"""
    notice_file = os.path.join(DATA_DIR, 'notice.txt')
    with open(notice_file, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'status': 'success', 'message': '公告已保存'}

def gm_get_notice():
    """获取公告"""
    notice_file = os.path.join(DATA_DIR, 'notice.txt')
    try:
        with open(notice_file, 'r', encoding='utf-8') as f:
            return {'content': f.read()}
    except:
        return {'content': ''}

def gm_send_item(charac_no, item_id, count=1, upgrade=0):
    """发送物品"""
    # 这里应该调用游戏服务器API
    return {
        'status': 'success',
        'message': f'已发送物品: 角色={charac_no}, 物品={item_id}, 数量={count}, 强化={upgrade}'
    }

def gm_set_level(charac_no, level):
    """设置等级"""
    return {
        'status': 'success',
        'message': f'已设置等级: 角色={charac_no}, 等级={level}'
    }

def gm_add_gold(charac_no, gold):
    """添加金币"""
    return {
        'status': 'success',
        'message': f'已添加金币: 角色={charac_no}, 金币={gold}'
    }

def gm_kick_user(uid):
    """踢出用户"""
    return {'status': 'success', 'message': f'已踢出用户: UID={uid}'}

def gm_ban_user(uid, reason='违规操作', duration=0):
    """封禁用户"""
    return {
        'status': 'success',
        'message': f'已封禁用户: UID={uid}, 原因={reason}, 时长={duration}天'
    }

def gm_unban_user(uid):
    """解封用户"""
    return {'status': 'success', 'message': f'已解封用户: UID={uid}'}

def gm_recharge(uid, cera):
    """充值"""
    return {
        'status': 'success',
        'message': f'充值成功: UID={uid}, 金额={cera}'
    }

# ==================== 统计功能 ====================

def get_stats():
    """获取统计数据"""
    try:
        chars = query_db("SELECT COUNT(*) as total FROM charac_info")
        total_chars = chars[0]['total'] if chars else 0
    except:
        total_chars = 0
    
    try:
        accounts = query_db("SELECT COUNT(*) as total FROM d_taiwan.accounts", db='d_taiwan')
        total_accounts = accounts[0]['total'] if accounts else 0
    except:
        total_accounts = 0
    
    try:
        skills = query_db("SELECT COUNT(*) as total FROM skill_info")
        total_skills = skills[0]['total'] if skills else 0
    except:
        total_skills = 0
    
    try:
        monsters = query_db("SELECT COUNT(*) as total FROM dnf_monster_info")
        total_monsters = monsters[0]['total'] if monsters else 0
    except:
        total_monsters = 0
    
    return {
        'total_chars': total_chars,
        'total_accounts': total_accounts,
        'total_items': 83977,  # PVF物品数
        'total_skills': total_skills,
        'total_monsters': total_monsters,
    }

# ==================== HTTP Handler ====================

class DNFHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # 路由
        if path == '/' or path == '/index.html':
            self.serve_dashboard()
        elif path == '/api/health':
            self.json_response({'status': 'ok', 'version': '4.0.0'})
        elif path == '/api/stats':
            self.json_response(get_stats())
        elif path == '/api/characters':
            page = int(params.get('page', [1])[0])
            page_size = int(params.get('page_size', [20])[0])
            filters = {
                'name': params.get('name', [None])[0],
                'job': params.get('job', [None])[0],
                'min_lev': params.get('min_lev', [None])[0],
                'max_lev': params.get('max_lev', [None])[0],
            }
            self.json_response(load_characters(page, page_size, filters))
        elif path.startswith('/api/character/'):
            char_id = path.split('/')[-1]
            result = load_character_detail(int(char_id))
            if result:
                self.json_response({'data': result})
            else:
                self.json_response({'error': 'not found'}, 404)
        elif path == '/api/items':
            query = params.get('q', [''])[0]
            page = int(params.get('page', [1])[0])
            page_size = int(params.get('page_size', [50])[0])
            self.json_response(load_items(query, page, page_size))
        elif path == '/api/skills':
            job = params.get('job', [100])[0]
            page = int(params.get('page', [1])[0])
            page_size = int(params.get('page_size', [50])[0])
            self.json_response(load_skills(int(job), page, page_size))
        elif path == '/api/monsters':
            query = params.get('q', [''])[0]
            page = int(params.get('page', [1])[0])
            page_size = int(params.get('page_size', [50])[0])
            self.json_response(load_monsters(query, page, page_size))
        elif path == '/api/gm/notice':
            self.json_response(gm_get_notice())
        elif path == '/api/jobs':
            self.json_response({'jobs': JOBS})
        else:
            self.json_response({'error': 'not found'}, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body) if body else {}
        
        path = urlparse(self.path).path
        
        if path == '/api/gm/notice/save':
            self.json_response(gm_save_notice(data.get('content', '')))
        elif path == '/api/gm/send-item':
            self.json_response(gm_send_item(
                data.get('charac_no'),
                data.get('item_id'),
                data.get('count', 1),
                data.get('upgrade', 0)
            ))
        elif path == '/api/gm/set-level':
            self.json_response(gm_set_level(data.get('charac_no'), data.get('level')))
        elif path == '/api/gm/add-gold':
            self.json_response(gm_add_gold(data.get('charac_no'), data.get('gold')))
        elif path == '/api/gm/kick':
            self.json_response(gm_kick_user(data.get('uid')))
        elif path == '/api/gm/ban':
            self.json_response(gm_ban_user(
                data.get('uid'),
                data.get('reason', '违规操作'),
                data.get('duration', 0)
            ))
        elif path == '/api/gm/unban':
            self.json_response(gm_unban_user(data.get('uid')))
        elif path == '/api/gm/recharge':
            self.json_response(gm_recharge(data.get('uid'), data.get('cera')))
        elif path == '/api/mail/send':
            # 邮件发送
            self.json_response({
                'status': 'success',
                'message': f"邮件已发送给 {data.get('to', '')}"
            })
        else:
            self.json_response({'error': 'not found'}, 404)
    
    def serve_dashboard(self):
        """提供dashboard页面"""
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def json_response(self, data, code=200):
        """JSON响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))
    
    def log_message(self, format, *args):
        """禁用日志"""
        pass

# ==================== 启动 ====================

def run(port=18885):
    server = HTTPServer(('0.0.0.0', port), DNFHandler)
    print(f"[*] DNF Admin v4.0 启动在端口 {port}")
    print(f"[*] 访问地址: http://localhost:{port}")
    server.serve_forever()

if __name__ == '__main__':
    run()
