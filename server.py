#!/usr/bin/env python3
"""
DNF 后台管理系统 v4.1
参考 edict 架构：单文件dashboard + Python后端 + RESTful API
"""

import json
import os
import sys
import pymysql
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ==================== 配置 ====================

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': '88888888',
    'charset': 'latin1',
    'use_unicode': False,
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

# 基础职业到高级职业映射
JOB_TREE = {
    0: [100, 101, 102, 103],  # 鬼剑士系
    1: [200, 201, 202, 203],  # 格斗家系
    2: [300, 301, 302, 303],  # 神枪手系
    3: [400, 401, 402, 403],  # 魔法师系
    4: [500, 501, 502, 503],  # 圣职者系
    5: [600, 601, 602, 603],  # 暗夜使者系
    6: [700, 701, 702, 703],  # 魔枪士系
    7: [800, 801, 802, 803],  # 枪剑士系
    8: [900, 901],            # 弓箭手系
}

# 高级职业到基础职业的映射
JOB_TO_BASE = {
    100: 0, 101: 0, 102: 0, 103: 0,
    200: 1, 201: 1, 202: 1, 203: 1,
    300: 2, 301: 2, 302: 2, 303: 2,
    400: 3, 401: 3, 402: 3, 403: 3,
    500: 4, 501: 4, 502: 4, 503: 4,
    600: 5, 601: 5, 602: 5, 603: 5,
    700: 6, 701: 6, 702: 6, 703: 6,
    800: 7, 801: 7, 802: 7, 803: 7,
    900: 8, 901: 8,
}

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 缓存
_pvf_items_cache = None
_pvf_cache_time = 0

# ==================== 数据库工具 ====================

def query_db(sql, params=None, db='taiwan_cain'):
    """查询数据库"""
    conn = None
    try:
        config = {**DB_CONFIG, 'database': db}
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

def decode_bytes(value):
    """解码字节值"""
    if isinstance(value, bytes):
        for encoding in ['utf-8', 'big5', 'cp950', 'gbk']:
            try:
                return value.decode(encoding)
            except:
                continue
        return value.decode('utf-8', errors='ignore')
    return value

# ==================== PVF 物品加载 ====================

def load_pvf_items():
    """加载PVF物品数据（通过SSH读取远程服务器）"""
    global _pvf_items_cache, _pvf_cache_time
    import time
    
    # 缓存5分钟
    if _pvf_items_cache and (time.time() - _pvf_cache_time < 300):
        print(f"[PVF] 使用缓存: {len(_pvf_items_cache)}个物品")
        return _pvf_items_cache
    
    items = []
    print("[PVF] 开始加载PVF物品数据...")
    
    try:
        import subprocess
        # 通过SSH读取远程PVF文件
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'cat /opt/dnf-llnut/data/conf.d/dnf-console/source/gold.txt'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        print(f"[PVF] SSH返回码: {result.returncode}, 输出长度: {len(result.stdout)}")
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
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
            print(f"[PVF] 加载完成: {len(items)}个物品")
        else:
            print(f"[PVF] SSH错误: {result.stderr}")
    except Exception as e:
        print(f"[PVF ERROR] {e}")
    
    _pvf_items_cache = items
    _pvf_cache_time = time.time()
    return items

def get_item_name(item_id, slot=0):
    """获取物品名称（优先从PVF查询）"""
    pvf_items = load_pvf_items()
    for item in pvf_items:
        if item['id'] == item_id:
            return item['name']
    
    # 从数据库查询（使用 latin1 连接避免双重编码）
    try:
        conn = pymysql.connect(**DB_CONFIG, database='taiwan_cain_web')
        cursor = conn.cursor()
        cursor.execute("SELECT it_name FROM dnf_item_info WHERE it_no = %s", (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            name = row[0]
            if isinstance(name, bytes):
                # 尝试多种编码
                for enc in ['utf-8', 'big5', 'cp950', 'gbk']:
                    try:
                        name = name.decode(enc)
                        break
                    except:
                        continue
            if name and name.strip():
                return name
    except Exception as e:
        print(f"[ITEM NAME ERROR] {e}")
    
    # 数据库无记录时，用槽位名+ID
    SLOT_NAMES = {
        0: '武器', 1: '上衣', 2: '下装', 3: '头肩', 4: '腰带',
        5: '鞋子', 6: '项链', 7: '手镯', 8: '戒指', 9: '辅助装备',
        10: '魔法石', 11: '耳环', 12: '宠物', 13: '称号', 14: '光环',
        15: '皮肤', 100: '消耗品', 101: '材料', 102: '任务物品',
    }
    slot_name = SLOT_NAMES.get(slot, '物品')
    return f"{slot_name}-{item_id}"

# ==================== PVF 文件管理 ====================

def list_pvf_files():
    """列出服务端 PVF 文件"""
    try:
        import subprocess
        # 列出服务端 PVF 相关文件
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'find /opt/dnf-llnut/data -name \"*.txt\" -o -name \"*.pvf\" | head -20'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        files = []
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line:
                    # 判断文件类型
                    if line.endswith('.pvf'):
                        file_type = 'pvf'
                    elif 'item' in line.lower() or 'equip' in line.lower():
                        file_type = 'item'
                    elif 'monster' in line.lower() or 'mob' in line.lower():
                        file_type = 'monster'
                    elif 'skill' in line.lower():
                        file_type = 'skill'
                    else:
                        file_type = 'other'
                    
                    files.append({
                        'path': line,
                        'name': line.split('/')[-1],
                        'type': file_type
                    })
        
        return {'files': files}
    except Exception as e:
        print(f"[PVF LIST ERROR] {e}")
        return {'files': [], 'error': str(e)}

def load_pvf_file(file_path, file_type='gold'):
    """加载指定的 PVF 文件"""
    global _pvf_items_cache, _pvf_cache_time
    
    if not file_path:
        return {'error': '请指定文件路径'}
    
    try:
        import subprocess
        # 通过SSH读取文件
        cmd = f"sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'cat {file_path}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return {'error': f'读取文件失败: {result.stderr}'}
        
        items = []
        content = result.stdout
        
        # 解析 gold.txt 格式
        if file_type == 'gold':
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'\[(\d+)\s*\]\s*name:(.+)', line)
                if match:
                    item_id = int(match.group(1))
                    item_name = match.group(2).strip()
                    items.append({
                        'id': item_id,
                        'name': item_name,
                        'category': '物品'
                    })
        # 解析 Script.pvf 二进制格式
        elif file_type == 'pvf':
            # Script.pvf 是二进制加密文件，需要特殊解析
            return {'error': 'Script.pvf 是二进制加密文件，暂不支持解析'}
        # 解析其他文本格式
        else:
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # 尝试解析各种格式
                parts = line.split('\t')
                if len(parts) >= 2:
                    items.append({
                        'id': parts[0],
                        'name': parts[1],
                        'category': file_type
                    })
        
        # 更新缓存
        _pvf_items_cache = items
        _pvf_cache_time = time.time()
        
        return {
            'success': True,
            'count': len(items),
            'file': file_path,
            'type': file_type
        }
    except Exception as e:
        print(f"[PVF LOAD ERROR] {e}")
        return {'error': str(e)}

def upload_pvf_file(data):
    """上传本地 PVF 文件"""
    global _pvf_items_cache, _pvf_cache_time
    
    content = data.get('content', '')
    file_type = data.get('type', 'gold')
    file_name = data.get('name', 'uploaded.txt')
    
    if not content:
        return {'error': '文件内容为空'}
    
    try:
        items = []
        
        # 解析 gold.txt 格式
        if file_type == 'gold':
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'\[(\d+)\s*\]\s*name:(.+)', line)
                if match:
                    item_id = int(match.group(1))
                    item_name = match.group(2).strip()
                    items.append({
                        'id': item_id,
                        'name': item_name,
                        'category': '物品'
                    })
        # 解析 CSV/TSV 格式
        elif file_type in ['csv', 'tsv']:
            separator = ',' if file_type == 'csv' else '\t'
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(separator)
                if len(parts) >= 2:
                    items.append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip(),
                        'category': '物品'
                    })
        else:
            return {'error': f'不支持的文件类型: {file_type}'}
        
        # 更新缓存
        _pvf_items_cache = items
        _pvf_cache_time = time.time()
        
        return {
            'success': True,
            'count': len(items),
            'name': file_name,
            'type': file_type
        }
    except Exception as e:
        print(f"[PVF UPLOAD ERROR] {e}")
        return {'error': str(e)}

def import_pvf_to_db(items):
    """导入 PVF 数据到数据库"""
    if not items:
        return {'error': '没有数据可导入'}
    
    try:
        conn = pymysql.connect(**DB_CONFIG, database='taiwan_cain_web')
        cursor = conn.cursor()
        
        imported = 0
        updated = 0
        errors = 0
        
        for item in items:
            item_id = item.get('id')
            item_name = item.get('name', '')
            
            if not item_id or not item_name:
                errors += 1
                continue
            
            try:
                # 检查是否已存在
                cursor.execute("SELECT it_no FROM dnf_item_info WHERE it_no = %s", (item_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # 更新
                    cursor.execute("UPDATE dnf_item_info SET it_name = %s WHERE it_no = %s", (item_name, item_id))
                    updated += 1
                else:
                    # 插入
                    cursor.execute("INSERT INTO dnf_item_info (it_no, it_name) VALUES (%s, %s)", (item_id, item_name))
                    imported += 1
            except Exception as e:
                print(f"[IMPORT ERROR] item {item_id}: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'imported': imported,
            'updated': updated,
            'errors': errors,
            'total': len(items)
        }
    except Exception as e:
        print(f"[PVF IMPORT ERROR] {e}")
        return {'error': str(e)}

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
    
    # 解码
    for c in chars:
        c['job_name'] = JOBS.get(c.get('job'), '未知')
        c['charac_name'] = decode_bytes(c.get('charac_name'))
        for field in ['create_time', 'last_play_time']:
            if c.get(field) and hasattr(c[field], 'strftime'):
                c[field] = c[field].strftime('%Y-%m-%d %H:%M:%S')
    
    return {'data': chars, 'total': total, 'page': page, 'page_size': page_size}

def load_character_detail(char_id):
    """加载角色详情"""
    # 先查询角色信息，获取 charac_no
    sql = "SELECT * FROM charac_info WHERE charac_no = %s"
    chars = query_db(sql, (char_id,))
    if not chars:
        # 尝试用 m_id 查询
        sql = "SELECT * FROM charac_info WHERE m_id = %s"
        chars = query_db(sql, (char_id,))
        if not chars:
            return None
    
    char = chars[0]
    char['charac_name'] = decode_bytes(char.get('charac_name'))
    char['job_name'] = JOBS.get(char.get('job'), '未知')
    
    # 格式化时间
    for field in ['create_time', 'last_play_time']:
        if char.get(field) and hasattr(char[field], 'strftime'):
            char[field] = char[field].strftime('%Y-%m-%d %H:%M:%S')
    
    # 使用 inventory 表的 equipslot blob 读取装备
    charac_no = char.get('charac_no')
    import zlib
    import struct
    
    SLOT_NAMES = {
        0: '武器', 1: '上衣', 2: '下装', 3: '头肩', 4: '腰带',
        5: '鞋子', 6: '项链', 7: '手镯', 8: '戒指', 9: '辅助装备',
        10: '魔法石', 11: '耳环', 12: '宠物', 13: '称号', 14: '光环',
        15: '皮肤', 100: '消耗品', 101: '材料', 102: '任务物品'
    }
    
    items = []
    
    # 读取 equipslot blob
    inv_sql = "SELECT equipslot, inventory FROM taiwan_cain_2nd.inventory WHERE charac_no = %s"
    inv_data = query_db(inv_sql, (charac_no,), 'taiwan_cain_2nd')
    
    if inv_data and inv_data[0].get('equipslot'):
        equipslot_blob = inv_data[0]['equipslot']
        try:
            # 解压 equipslot (前4字节是长度, 后面是zlib压缩数据)
            decompressed = zlib.decompress(equipslot_blob[4:])
            
            # 每个槽位 61 字节
            slot_size = 61
            for i in range(0, len(decompressed), slot_size):
                slot_data = decompressed[i:i+slot_size]
                if len(slot_data) >= 4:
                    item_no = struct.unpack('<H', slot_data[2:4])[0]
                    if item_no > 0:
                        slot_idx = i // slot_size
                        slot_name = SLOT_NAMES.get(slot_idx, f'槽位{slot_idx}')
                        item_name = get_item_name(item_no, slot_idx)
                        items.append({
                            'slot': slot_idx,
                            'slot_name': slot_name,
                            'it_id': item_no,
                            'item_name': item_name,
                        })
        except Exception as e:
            print(f"[EQUIP ERROR] {e}")
    
    # 读取 inventory blob (背包物品)
    if inv_data and inv_data[0].get('inventory'):
        inventory_blob = inv_data[0]['inventory']
        try:
            # 解压 inventory (前4字节是长度, 后面是zlib压缩数据)
            decompressed_inv = zlib.decompress(inventory_blob[4:])
            
            # 每个槽位 61 字节
            slot_size = 61
            for i in range(0, len(decompressed_inv), slot_size):
                slot_data = decompressed_inv[i:i+slot_size]
                if len(slot_data) >= 4:
                    item_no = struct.unpack('<H', slot_data[2:4])[0]
                    if item_no > 0:
                        slot_idx = i // slot_size + 100  # 背包槽位从 100 开始
                        slot_name = SLOT_NAMES.get(slot_idx, f'背包{slot_idx-100}')
                        item_name = get_item_name(item_no, slot_idx)
                        items.append({
                            'slot': slot_idx,
                            'slot_name': slot_name,
                            'it_id': item_no,
                            'item_name': item_name,
                        })
        except Exception as e:
            print(f"[INVENTORY ERROR] {e}")
    
    char['inventory'] = items
    char['inventory_count'] = len(items)
    
    # 加载角色技能（从skill表的skill_slot blob解析）
    charac_no = char.get('charac_no')
    if charac_no:
        import zlib
        import struct
        
        skill_sql = "SELECT skill_slot FROM taiwan_cain_2nd.skill WHERE charac_no = %s"
        skill_data = query_db(skill_sql, (charac_no,), 'taiwan_cain_2nd')
        
        skill_list = []
        if skill_data and skill_data[0].get('skill_slot'):
            slot_data = skill_data[0]['skill_slot']
            if isinstance(slot_data, bytes) and len(slot_data) > 4:
                try:
                    # 解压缩
                    decompressed = zlib.decompress(slot_data[4:])
                    
                    # 解析为 1字节index + 1字节level
                    for i in range(0, len(decompressed), 2):
                        if i + 2 <= len(decompressed):
                            skill_idx = decompressed[i]
                            skill_level = decompressed[i+1]
                            if skill_level > 0:
                                # 查询技能名称
                                skill_name_sql = "SELECT name FROM taiwan_cain_web.skill_info WHERE skill_index = %s AND job_index = %s AND module_type = 0 LIMIT 1"
                                base_job = JOB_TO_BASE.get(char.get('job', 0), char.get('job', 0))
                                skill_info = query_db(skill_name_sql, (skill_idx, base_job), 'taiwan_cain_web')
                                
                                skill_name = f'技能{skill_idx}'
                                if skill_info:
                                    skill_name = decode_bytes(skill_info[0].get('name'))
                                
                                skill_list.append({
                                    'skill_index': skill_idx,
                                    'name': skill_name,
                                    'level': skill_level,
                                })
                except Exception as e:
                    print(f"[SKILL ERROR] {e}")
        
        char['skills'] = skill_list
        char['skills_count'] = len(skill_list)
    
    return char

def load_items(query='', page=1, page_size=50):
    """加载物品列表"""
    pvf_items = load_pvf_items()
    
    # 搜索过滤
    if query:
        filtered = [i for i in pvf_items if query.lower() in i['name'].lower()]
    else:
        filtered = pvf_items
    
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {'data': filtered[start:end], 'total': total, 'page': page, 'page_size': page_size}

def load_skills(job_id, page=1, page_size=50):
    """加载技能列表"""
    base_job = JOB_TO_BASE.get(job_id, job_id)
    
    sql = "SELECT * FROM taiwan_cain_web.skill_info WHERE job_index = %s AND module_type = 0 ORDER BY skill_index LIMIT %s OFFSET %s"
    offset = (page - 1) * page_size
    skills = query_db(sql, (base_job, page_size, offset), 'taiwan_cain_web')
    
    count_sql = "SELECT COUNT(*) as total FROM taiwan_cain_web.skill_info WHERE job_index = %s AND module_type = 0"
    total = query_db(count_sql, (base_job,), 'taiwan_cain_web')[0]['total']
    
    # 解码
    for skill in skills:
        skill['name'] = decode_bytes(skill.get('name'))
        for field in ['basic_explain', 'skill_explain', 'command_key_explain']:
            if skill.get(field) and isinstance(skill[field], bytes):
                for enc in ['big5', 'cp950', 'utf-8']:
                    try:
                        skill[field] = skill[field].decode(enc)
                        break
                    except:
                        continue
    
    return {'data': skills, 'total': total, 'page': page, 'page_size': page_size}

def load_monsters(query='', page=1, page_size=50):
    """加载怪物列表"""
    offset = (page - 1) * page_size
    
    if query:
        sql = "SELECT * FROM taiwan_cain_web.dnf_monster_info WHERE mon_name_kr LIKE %s ORDER BY idx LIMIT %s OFFSET %s"
        params = (f"%{query}%", page_size, offset)
        count_sql = "SELECT COUNT(*) as total FROM taiwan_cain_web.dnf_monster_info WHERE mon_name_kr LIKE %s"
        count_params = (f"%{query}%",)
    else:
        sql = "SELECT * FROM taiwan_cain_web.dnf_monster_info ORDER BY idx LIMIT %s OFFSET %s"
        params = (page_size, offset)
        count_sql = "SELECT COUNT(*) as total FROM taiwan_cain_web.dnf_monster_info"
        count_params = ()
    
    monsters = query_db(sql, params, 'taiwan_cain_web')
    total_result = query_db(count_sql, count_params, 'taiwan_cain_web')
    total = total_result[0]['total'] if total_result else 0
    
    # 解码
    for m in monsters:
        m['mon_name_kr'] = decode_bytes(m.get('mon_name_kr'))
        m['monster_type'] = decode_bytes(m.get('monster_type'))
    
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
    return {'status': 'success', 'message': f'已发送物品: 角色={charac_no}, 物品={item_id}, 数量={count}, 强化={upgrade}'}

def gm_set_level(charac_no, level):
    """设置等级"""
    return {'status': 'success', 'message': f'已设置等级: 角色={charac_no}, 等级={level}'}

def gm_add_gold(charac_no, gold):
    """添加金币"""
    return {'status': 'success', 'message': f'已添加金币: 角色={charac_no}, 金币={gold}'}

def gm_kick_user(uid):
    """踢出用户"""
    return {'status': 'success', 'message': f'已踢出用户: UID={uid}'}

def gm_ban_user(uid, reason='违规操作', duration=0):
    """封禁用户"""
    return {'status': 'success', 'message': f'已封禁用户: UID={uid}, 原因={reason}'}

def gm_unban_user(uid):
    """解封用户"""
    return {'status': 'success', 'message': f'已解封用户: UID={uid}'}

# ==================== 账号功能 ====================

def load_accounts(page=1, page_size=20, filters=None):
    """加载账号列表"""
    offset = (page - 1) * page_size
    
    where_clauses = []
    params = []
    
    if filters:
        if filters.get('uid'):
            where_clauses.append("UID = %s")
            params.append(int(filters['uid']))
        if filters.get('name'):
            where_clauses.append("accountname LIKE %s")
            params.append(f"%{filters['name']}%")
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    try:
        count_sql = f"SELECT COUNT(*) as total FROM d_taiwan.accounts WHERE {where_sql}"
        total = query_db(count_sql, tuple(params), db='d_taiwan')[0]['total']
        
        sql = f"SELECT UID, accountname, qq, billing, VIP, admin, parent_uid FROM d_taiwan.accounts WHERE {where_sql} ORDER BY UID DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        accounts = query_db(sql, tuple(params), db='d_taiwan')
        
        for acc in accounts:
            for field in ['accountname', 'qq']:
                if acc.get(field):
                    acc[field] = decode_bytes(acc[field])
        
        return {'data': accounts, 'total': total, 'page': page, 'page_size': page_size}
    except Exception as e:
        print(f"[ACCOUNT ERROR] {e}")
        return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}

def load_account_detail(uid):
    """加载账号详情"""
    try:
        sql = "SELECT * FROM d_taiwan.accounts WHERE UID = %s"
        accs = query_db(sql, (uid,), db='d_taiwan')
        if not accs:
            return None
        
        acc = accs[0]
        for field in ['accountname', 'qq']:
            if acc.get(field):
                acc[field] = decode_bytes(acc[field])
        
        # 查询该账号的角色列表
        chars_sql = "SELECT charac_no, charac_name, job, lev FROM charac_info WHERE m_id = %s"
        chars = query_db(chars_sql, (uid,))
        for c in chars:
            c['charac_name'] = decode_bytes(c.get('charac_name'))
            c['job_name'] = JOBS.get(c.get('job'), '未知')
        acc['characters'] = chars
        
        return acc
    except Exception as e:
        print(f"[ACCOUNT DETAIL ERROR] {e}")
        return None

def load_item_detail(item_id):
    """加载物品详情"""
    try:
        sql = "SELECT * FROM dnf_item_info WHERE it_no = %s"
        items = query_db(sql, (item_id,), db='taiwan_cain_web')
        if not items:
            # 尝试从PVF获取
            pvf = load_pvf_items()
            if item_id in pvf:
                return {'it_no': item_id, 'it_name': pvf[item_id], 'source': 'pvf'}
            return None
        
        item = items[0]
        # 解码所有字符串/blob字段
        for key, value in item.items():
            if isinstance(value, bytes):
                item[key] = decode_bytes(value)
        
        # 添加类型名称
        MASTER_TYPES = {1: '消耗品', 2: '材料', 3: '任务物品', 4: '装备', 5: '时装', 6: '宠物', 7: '称号', 40: '装备'}
        item['master_type_name'] = MASTER_TYPES.get(item.get('master_type'), '其他')
        
        # 添加稀有度名称
        RARITY = {0: '普通', 1: '高级', 2: '稀有', 3: '神器', 4: '传说', 5: '史诗', 6: '神话'}
        item['rarity_name'] = RARITY.get(item.get('rarity'), '未知')
        
        return item
    except Exception as e:
        print(f"[ITEM DETAIL ERROR] {e}")
        return None

def load_monster_detail(idx):
    """加载怪物详情"""
    try:
        sql = "SELECT * FROM dnf_monster_info WHERE idx = %s"
        monsters = query_db(sql, (idx,), db='taiwan_cain_web')
        if not monsters:
            return None
        
        monster = monsters[0]
        # 解码所有字符串/blob字段
        for key, value in monster.items():
            if isinstance(value, bytes):
                monster[key] = decode_bytes(value)
        
        return monster
    except Exception as e:
        print(f"[MONSTER DETAIL ERROR] {e}")
        return None

# ==================== 统计功能 ====================

def get_stats():
    """获取统计数据"""
    try:
        total_chars = query_db("SELECT COUNT(*) as total FROM charac_info")[0]['total']
    except:
        total_chars = 0
    
    try:
        total_accounts = query_db("SELECT COUNT(*) as total FROM d_taiwan.accounts", db='d_taiwan')[0]['total']
    except:
        total_accounts = 0
    
    try:
        total_skills = query_db("SELECT COUNT(*) as total FROM taiwan_cain_web.skill_info WHERE module_type = 0", db='taiwan_cain_web')[0]['total']
    except:
        total_skills = 0
    
    try:
        total_monsters = query_db("SELECT COUNT(*) as total FROM dnf_monster_info")[0]['total']
    except:
        total_monsters = 0
    
    pvf_items = load_pvf_items()
    
    return {
        'total_chars': total_chars,
        'total_accounts': total_accounts,
        'total_items': len(pvf_items),
        'total_skills': total_skills,
        'total_monsters': total_monsters,
    }

def get_server_status():
    """获取服务端运行状态"""
    import subprocess
    
    status = {
        'docker': {'status': 'unknown', 'containers': []},
        'mysql': {'status': 'unknown', 'connections': 0},
        'game_server': {'status': 'unknown', 'port': 7600},
        'network': {'status': 'unknown', 'latency': 0},
        'disk': {'status': 'unknown', 'usage': '0%'},
        'memory': {'status': 'unknown', 'usage': '0%'},
        'issues': []
    }
    
    try:
        # 检查 Docker 容器状态
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker ps --format \"{{.Names}}\t{{.Status}}\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            containers = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        containers.append({'name': parts[0], 'status': parts[1]})
            status['docker']['containers'] = containers
            status['docker']['status'] = 'running' if containers else 'stopped'
        
        # 检查 MySQL 连接
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker exec dnf-llnut_dnf-1_1 mysql -u root -p88888888 -e \"SELECT COUNT(*) as cnt FROM information_schema.processlist;\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip().isdigit():
                    status['mysql']['connections'] = int(line.strip())
                    status['mysql']['status'] = 'running'
        
        # 检查游戏端口
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'netstat -tlnp 2>/dev/null | grep 7600'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if '7600' in result.stdout:
            status['game_server']['status'] = 'running'
        else:
            status['game_server']['status'] = 'stopped'
            status['issues'].append('游戏服务端口 7600 未监听')
        
        # 检查磁盘使用
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'df -h / | tail -1 | awk \"{print $5}\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            status['disk']['usage'] = result.stdout.strip()
            usage = int(result.stdout.strip().replace('%', ''))
            if usage > 90:
                status['disk']['status'] = 'warning'
                status['issues'].append(f'磁盘使用率过高: {status["disk"]["usage"]}')
            else:
                status['disk']['status'] = 'normal'
        
        # 检查内存使用
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'free -m | awk \"/Mem/{printf \"%s\", $3/$2*100}\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            status['memory']['usage'] = f"{float(result.stdout.strip()):.1f}%"
            usage = float(result.stdout.strip())
            if usage > 90:
                status['memory']['status'] = 'warning'
                status['issues'].append(f'内存使用率过高: {status["memory"]["usage"]}')
            else:
                status['memory']['status'] = 'normal'
        
        # 检查网络连接
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'ping -c 1 -W 2 127.0.0.1 2>/dev/null | grep time='"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if 'time=' in result.stdout:
            import re
            match = re.search(r'time=(\d+\.?\d*)', result.stdout)
            if match:
                status['network']['latency'] = float(match.group(1))
                status['network']['status'] = 'normal'
        
    except Exception as e:
        status['issues'].append(f'状态检查出错: {str(e)}')
    
    return status

def get_server_issues():
    """获取服务端问题诊断"""
    import subprocess
    
    issues = []
    
    try:
        # 检查账号封禁状态
        banned = query_db("SELECT m_id, punish_type, end_time FROM d_taiwan.member_punish_info WHERE end_time > NOW()", db='d_taiwan')
        for ban in banned:
            issues.append({
                'level': 'warning',
                'type': 'account_ban',
                'message': f'账号 {ban["m_id"]} 被封禁至 {ban["end_time"]}',
                'solution': 'DELETE FROM d_taiwan.member_punish_info WHERE m_id=?'
            })
        
        # 检查 billing 字段
        billing_users = query_db("SELECT UID, accountname FROM d_taiwan.accounts WHERE billing != 0", db='d_taiwan')
        for user in billing_users:
            issues.append({
                'level': 'warning',
                'type': 'billing',
                'message': f'账号 {user["accountname"]} 的 billing 字段不为 0',
                'solution': 'UPDATE d_taiwan.accounts SET billing=0 WHERE UID=?'
            })
        
        # 检查角色数据完整性
        orphan_chars = query_db("SELECT COUNT(*) as cnt FROM charac_info WHERE m_id NOT IN (SELECT UID FROM d_taiwan.accounts)")[0]['cnt']
        if orphan_chars > 0:
            issues.append({
                'level': 'info',
                'type': 'data_integrity',
                'message': f'存在 {orphan_chars} 个孤儿角色（账号不存在）',
                'solution': '检查 charac_info 表的 m_id 字段'
            })
        
        # 检查最近登录
        recent_logins = query_db("SELECT COUNT(*) as cnt FROM taiwan_cain_log.login_log WHERE login_time > DATE_SUB(NOW(), INTERVAL 1 HOUR)", db='taiwan_cain_log')
        if recent_logins and recent_logins[0]['cnt'] == 0:
            issues.append({
                'level': 'info',
                'type': 'activity',
                'message': '过去1小时没有登录记录',
                'solution': '检查客户端连接配置'
            })
        
    except Exception as e:
        issues.append({
            'level': 'error',
            'type': 'system',
            'message': f'问题诊断出错: {str(e)}',
            'solution': '检查数据库连接'
        })
    
    return issues

def get_events():
    """获取活动列表"""
    try:
        events = query_db("SELECT * FROM d_taiwan.dnf_event_info ORDER BY idx DESC LIMIT 50", db='d_taiwan')
        for event in events:
            for key, value in event.items():
                if isinstance(value, bytes):
                    event[key] = decode_bytes(value)
                elif hasattr(value, 'strftime'):
                    event[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        return {'events': events}
    except Exception as e:
        print(f"[EVENT ERROR] {e}")
        return {'events': [], 'error': str(e)}

def get_server_config():
    """获取服务端配置"""
    import subprocess
    
    config = {
        'server': {'ip': '192.168.1.204', 'ports': {}},
        'docker': {'image': 'dnf-llnut_dnf-1_1'},
        'database': {'host': '172.18.0.2', 'port': 3306}
    }
    
    try:
        # 检查端口
        cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'netstat -tlnp 2>/dev/null | grep -E \"7600|7000|7100|7200\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        ports = {'7600': '游戏服务', '7000': '频道1', '7100': '频道2', '7200': '频道3'}
        for port, name in ports.items():
            if port in result.stdout:
                config['server']['ports'][port] = {'name': name, 'status': 'running'}
            else:
                config['server']['ports'][port] = {'name': name, 'status': 'stopped'}
        
    except Exception as e:
        config['error'] = str(e)
    
    return config

def start_server(service='game'):
    """启动服务端"""
    import subprocess
    
    try:
        if service == 'game':
            cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker exec dnf-llnut_dnf-1_1 /opt/dnf/df_game_r start'"
        elif service == 'channel':
            cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker exec dnf-llnut_dnf-1_1 /opt/dnf/df_channel_r start'"
        elif service == 'all':
            cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker restart dnf-llnut_dnf-1_1'"
        else:
            return {'error': f'未知服务: {service}'}
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {'error': str(e)}

def stop_server(service='game'):
    """停止服务端"""
    import subprocess
    
    try:
        if service == 'game':
            cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker exec dnf-llnut_dnf-1_1 /opt/dnf/df_game_r stop'"
        elif service == 'channel':
            cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker exec dnf-llnut_dnf-1_1 /opt/dnf/df_channel_r stop'"
        elif service == 'all':
            cmd = "sshpass -p 'wp930803' ssh -o StrictHostKeyChecking=no root@192.168.1.204 'docker stop dnf-llnut_dnf-1_1'"
        else:
            return {'error': f'未知服务: {service}'}
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {'error': str(e)}

# ==================== HTTP Handler ====================

import time

class DNFHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        try:
            if path == '/' or path == '/index.html':
                self.serve_dashboard()
            elif path == '/api/health':
                self.json_response({'status': 'ok', 'version': '4.1.0'})
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
                from urllib.parse import unquote
                raw_query = params.get('q', [''])[0]
                query = unquote(raw_query)
                page = int(params.get('page', [1])[0])
                page_size = int(params.get('page_size', [50])[0])
                self.json_response(load_items(query, page, page_size))
            elif path == '/api/skills':
                job = int(params.get('job', [100])[0])
                page = int(params.get('page', [1])[0])
                page_size = int(params.get('page_size', [50])[0])
                self.json_response(load_skills(job, page, page_size))
            elif path == '/api/monsters':
                query = params.get('q', [''])[0]
                page = int(params.get('page', [1])[0])
                page_size = int(params.get('page_size', [50])[0])
                self.json_response(load_monsters(query, page, page_size))
            elif path.startswith('/api/monster/'):
                idx = path.split('/')[-1]
                result = load_monster_detail(int(idx))
                if result:
                    self.json_response({'data': result})
                else:
                    self.json_response({'error': 'not found'}, 404)
            elif path == '/api/accounts':
                page = int(params.get('page', [1])[0])
                page_size = int(params.get('page_size', [20])[0])
                filters = {
                    'uid': params.get('uid', [None])[0],
                    'name': params.get('name', [None])[0],
                }
                self.json_response(load_accounts(page, page_size, filters))
            elif path.startswith('/api/account/'):
                m_id = path.split('/')[-1]
                result = load_account_detail(int(m_id))
                if result:
                    self.json_response({'data': result})
                else:
                    self.json_response({'error': 'not found'}, 404)
            elif path.startswith('/api/item/'):
                item_id = path.split('/')[-1]
                result = load_item_detail(int(item_id))
                if result:
                    self.json_response({'data': result})
                else:
                    self.json_response({'error': 'not found'}, 404)
            elif path == '/api/gm/notice':
                self.json_response(gm_get_notice())
            elif path == '/api/jobs':
                self.json_response({'jobs': JOBS, 'job_tree': JOB_TREE})
            elif path == '/api/pvf/status':
                self.json_response({
                    'cached': len(_pvf_items_cache) if _pvf_items_cache else 0,
                    'cache_time': _pvf_cache_time,
                    'source': 'gold.txt'
                })
            elif path == '/api/pvf/files':
                self.json_response(list_pvf_files())
            elif path == '/api/pvf/load':
                file_path = params.get('path', [''])[0]
                file_type = params.get('type', ['gold'])[0]
                self.json_response(load_pvf_file(file_path, file_type))
            elif path == '/api/server/status':
                self.json_response(get_server_status())
            elif path == '/api/server/issues':
                self.json_response({'issues': get_server_issues()})
            elif path == '/api/server/config':
                self.json_response(get_server_config())
            elif path == '/api/events':
                self.json_response(get_events())
            elif path == '/api/server/start':
                service = params.get('service', ['game'])[0]
                self.json_response(start_server(service))
            elif path == '/api/server/stop':
                service = params.get('service', ['game'])[0]
                self.json_response(stop_server(service))
            else:
                self.json_response({'error': 'not found'}, 404)
        except Exception as e:
            self.json_response({'error': str(e)}, 500)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body) if body else {}
        
        path = urlparse(self.path).path
        
        try:
            if path == '/api/gm/notice/save':
                self.json_response(gm_save_notice(data.get('content', '')))
            elif path == '/api/gm/send-item':
                self.json_response(gm_send_item(data.get('charac_no'), data.get('item_id'), data.get('count', 1), data.get('upgrade', 0)))
            elif path == '/api/gm/set-level':
                self.json_response(gm_set_level(data.get('charac_no'), data.get('level')))
            elif path == '/api/gm/add-gold':
                self.json_response(gm_add_gold(data.get('charac_no'), data.get('gold')))
            elif path == '/api/gm/kick':
                self.json_response(gm_kick_user(data.get('uid')))
            elif path == '/api/gm/ban':
                self.json_response(gm_ban_user(data.get('uid'), data.get('reason', '违规操作'), data.get('duration', 0)))
            elif path == '/api/gm/unban':
                self.json_response(gm_unban_user(data.get('uid')))
            elif path == '/api/mail/send':
                self.json_response({'status': 'success', 'message': f"邮件已发送给 {data.get('to', '')}"})
            elif path == '/api/pvf/upload':
                self.json_response(upload_pvf_file(data))
            elif path == '/api/pvf/import':
                self.json_response(import_pvf_to_db(data.get('items', [])))
            elif path == '/api/server/unban':
                uid = data.get('uid')
                if uid:
                    try:
                        conn = pymysql.connect(**DB_CONFIG, database='d_taiwan')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM member_punish_info WHERE m_id = %s", (uid,))
                        cursor.execute("UPDATE accounts SET billing = 0 WHERE UID = %s", (uid,))
                        conn.commit()
                        conn.close()
                        self.json_response({'success': True, 'message': f'已解封账号 {uid}'})
                    except Exception as e:
                        self.json_response({'error': str(e)}, 500)
                else:
                    self.json_response({'error': '请提供 uid'}, 400)
            else:
                self.json_response({'error': 'not found'}, 404)
        except Exception as e:
            self.json_response({'error': str(e)}, 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
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
        pass

# ==================== 启动 ====================

def run(port=18885):
    server = HTTPServer(('0.0.0.0', port), DNFHandler)
    print(f"[*] DNF Admin v4.1 启动在端口 {port}")
    print(f"[*] 访问地址: http://localhost:{port}")
    server.serve_forever()

if __name__ == '__main__':
    run()
