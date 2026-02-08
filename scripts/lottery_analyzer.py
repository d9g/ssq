#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双色球开奖数据抓取与分析脚本

⚠️  重要免责声明 ⚠️
1. 本脚本仅用于技术学习和数据分析研究目的
2. 彩票开奖结果完全随机，历史数据无法预测未来结果
3. 本分析结果仅供参考，不构成任何投注建议
4. 请理性购彩，量力而行，未满18周岁禁止购买彩票
5. 开发者不承担因使用本脚本产生的任何损失

功能：
1. 抓取中国福利彩票双色球历史开奖数据
2. 分析开奖号码规律
3. 基于统计分析生成推荐号码
"""

import requests
import time
import json
import re
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
import warnings
import os
import hjson
import random
warnings.filterwarnings('ignore')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class DoubleColorBallAnalyzer:
    """双色球分析器"""
    
    def __init__(self):
        self.base_url = "https://www.cwl.gov.cn/ygkj/wqkjgg/"
        self.api_url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
        
        # 多个真实的User-Agent，用于轮换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        
        self.session = requests.Session()
        self.lottery_data = []
        
        # 配置session
        self._setup_session()
        
    def _setup_session(self):
        """配置session的基本设置"""
        # 设置连接池
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 设置基本headers
        self._update_headers()
    
    def _update_headers(self):
        """更新请求头，使用随机User-Agent"""
        user_agent = random.choice(self.user_agents)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        self.session.headers.update(headers)
        print(f"🔄 更新User-Agent: {user_agent[:50]}...")
        
    def get_max_pages(self):
        """获取真实的最大页码，增强错误处理"""
        print("正在获取最大页码...")
        
        max_retries = 5
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 每次尝试都更新headers
                self._update_headers()
                
                # 先获取第一页数据来确定总数
                params = {
                    'name': 'ssq',
                    'pageNo': 1,
                    'pageSize': 30,
                    'systemType': 'PC'
                }
                
                # 添加随机延时
                # if attempt > 0:
                #     delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                #     print(f"⏳ 第 {attempt + 1} 次尝试，等待 {delay:.1f} 秒...")
                #     time.sleep(delay)
                # else:
                #     time.sleep(random.uniform(0, 1))  # 初始随机延时
                
                print(f"🌐 正在请求API... (尝试 {attempt + 1}/{max_retries})")
                response = self.session.get(self.api_url, params=params, timeout=30)
                
                print(f"📡 响应状态码: {response.status_code}")
                response.raise_for_status()
                
                data = response.json()
                print(f"📊 API响应: state={data.get('state')}, message={data.get('message')}")
                
                if data.get('state') != 0:
                    print(f"❌ API返回错误: {data.get('message', '未知错误')}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return 100  # 默认返回100页
                
                # 尝试获取总记录数
                total_count = data.get('total', 0)
                if total_count > 0:
                    max_pages = (total_count + 29) // 30  # 向上取整
                    print(f"✅ 发现总共 {total_count} 条记录，需要抓取 {max_pages} 页")
                    return max_pages
                
                # 如果无法获取总数，通过试探方式确定最大页码
                print("无法获取总记录数，正在试探最大页码...")
                page = 1
                while page <= 200:  # 设置上限防止无限循环
                    params['pageNo'] = page
                    response = self.session.get(self.api_url, params=params, timeout=30)
                    data = response.json()
                    
                    if data.get('state') != 0 or not data.get('result'):
                        break
                    
                    page += 10  # 每次跳跃10页快速试探
                    time.sleep(0.2)
                
                # 精确定位最大页码
                start = max(1, page - 10)
                end = page
                
                for precise_page in range(start, end + 1):
                    params['pageNo'] = precise_page
                    response = self.session.get(self.api_url, params=params, timeout=30)
                    data = response.json()
                    
                    if data.get('state') != 0 or not data.get('result'):
                        max_pages = precise_page - 1
                        print(f"✅ 通过试探确定最大页码为 {max_pages}")
                        return max_pages
                    
                    time.sleep(0.1)
                
                return max(1, page - 1)
                
            except requests.exceptions.Timeout:
                print(f"⏰ 请求超时 (尝试 {attempt + 1}/{max_retries})")
            except requests.exceptions.ConnectionError:
                print(f"🔌 连接错误 (尝试 {attempt + 1}/{max_retries})")
            except requests.exceptions.HTTPError as e:
                print(f"🌐 HTTP错误: {e} (尝试 {attempt + 1}/{max_retries})")
            except Exception as e:
                print(f"❌ 获取最大页码时出错: {e} (尝试 {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                print("🔄 准备重试...")
        
        print("⚠️  所有尝试都失败，使用默认页数 100")
        return 100
    
    def fetch_lottery_data(self, max_pages=10):
        """抓取双色球开奖数据，增强错误处理"""
        print("开始抓取双色球开奖数据...")
        
        consecutive_failures = 0
        max_consecutive_failures = 5
        successful_pages = 0
        
        for page in range(1, max_pages + 1):
            print(f"📄 正在抓取第 {page} 页数据...")
            
            # 重试机制
            max_retries = 5
            retry_count = 0
            success = False
            base_delay = 1
            
            while retry_count < max_retries and not success:
                try:
                    # 每隔几次请求更新headers
                    if page % 5 == 1 or retry_count > 0:
                        self._update_headers()
                    
                    # API参数
                    params = {
                        'name': 'ssq',  # 双色球
                        'pageNo': page,
                        'pageSize': 30,
                        'systemType': 'PC'
                    }
                    
                    # 计算延时
                    # if retry_count > 0:
                    #     # 指数退避延时，加上随机因子
                    #     delay = min(base_delay * (2 ** retry_count), 15) + random.uniform(0, 2)
                    #     print(f"⏳ 第 {retry_count + 1} 次重试，等待 {delay:.1f} 秒...")
                    #     time.sleep(delay)
                    # else:
                    #     # 正常延时，避免请求过于频繁
                    #     delay = random.uniform(1, 2)  # 1-2秒随机延时
                    #     time.sleep(delay)
                    
                    print(f"🌐 发送请求到API... (页面 {page}, 尝试 {retry_count + 1})")
                    response = self.session.get(self.api_url, params=params, timeout=30)
                    
                    print(f"📡 响应状态码: {response.status_code}")
                    response.raise_for_status()
                    
                    # 解析JSON响应
                    data = response.json()
                    print(f"📊 API响应解析: state={data.get('state')}")
                    
                    if data.get('state') != 0:
                        print(f"❌ API返回错误: {data.get('message', '未知错误')}")
                        retry_count += 1
                        continue
                    
                    results = data.get('result', [])
                    if not results:
                        print(f"📭 第 {page} 页无数据")
                        break
                    
                    print(f"✅ 第 {page} 页获取到 {len(results)} 条记录")
                    consecutive_failures = 0  # 重置连续失败计数
                    successful_pages += 1
                    
                    for item in results:
                        try:
                            # 解析期号
                            period = item.get('code', '')
                            
                            # 解析开奖日期
                            date_str = item.get('date', '')
                            # 提取日期部分，去除星期信息
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
                            if not date_match:
                                continue
                            draw_date = date_match.group(1)
                            
                            # 解析红球号码（逗号分隔的字符串）
                            red_str = item.get('red', '')
                            if not red_str:
                                continue
                            red_balls = [int(x.strip()) for x in red_str.split(',')]
                            
                            # 解析蓝球号码
                            blue_str = item.get('blue', '')
                            if not blue_str:
                                continue
                            blue_ball = int(blue_str)
                            
                            # 解析其他信息
                            sales_amount = self._parse_number(item.get('sales', '0'))
                            pool_amount = self._parse_number(item.get('poolmoney', '0'))
                            
                            # 解析奖级信息
                            prizegrades = item.get('prizegrades', [])
                            first_prize_count = 0
                            first_prize_amount = 0
                            second_prize_count = 0
                            second_prize_amount = 0
                            
                            for grade in prizegrades:
                                if grade.get('type') == 1:  # 一等奖
                                    first_prize_count = self._parse_number(grade.get('typenum', '0'))
                                    first_prize_amount = self._parse_number(grade.get('typemoney', '0'))
                                elif grade.get('type') == 2:  # 二等奖
                                    second_prize_count = self._parse_number(grade.get('typenum', '0'))
                                    second_prize_amount = self._parse_number(grade.get('typemoney', '0'))
                            
                            # 存储数据
                            lottery_record = {
                                'period': period,
                                'date': draw_date,
                                'red_balls': red_balls,
                                'blue_ball': blue_ball,
                                'first_prize_count': first_prize_count,
                                'first_prize_amount': first_prize_amount,
                                'second_prize_count': second_prize_count,
                                'second_prize_amount': second_prize_amount,
                                'sales_amount': sales_amount,
                                'pool_amount': pool_amount
                            }
                            
                            self.lottery_data.append(lottery_record)
                            
                        except Exception as e:
                            print(f"⚠️  解析记录时出错: {e}")
                            continue
                    
                    success = True  # 标记成功
                    
                except requests.exceptions.Timeout:
                    print(f"⏰ 网络超时 (页面 {page}, 尝试 {retry_count + 1})")
                    retry_count += 1
                except requests.exceptions.ConnectionError:
                    print(f"🔌 连接错误 (页面 {page}, 尝试 {retry_count + 1})")
                    retry_count += 1
                except requests.exceptions.HTTPError as e:
                    print(f"🌐 HTTP错误: {e} (页面 {page}, 尝试 {retry_count + 1})")
                    retry_count += 1
                except Exception as e:
                    print(f"❌ 抓取第 {page} 页时出错: {e} (尝试 {retry_count + 1})")
                    retry_count += 1
                
                if retry_count >= max_retries:
                    consecutive_failures += 1
                    print(f"💥 第 {page} 页重试 {max_retries} 次后仍然失败，跳过此页")
                    break
            
            # 如果连续失败太多次，停止抓取
            if consecutive_failures >= max_consecutive_failures:
                print(f"🛑 连续 {max_consecutive_failures} 页失败，停止抓取以避免被封禁")
                break
        
        print(f"🎉 数据抓取完成！成功抓取 {successful_pages} 页，共获取 {len(self.lottery_data)} 期开奖数据")
        
        # 如果获取的数据太少，给出警告
        if len(self.lottery_data) < 100:
            print(f"⚠️  获取的数据较少 ({len(self.lottery_data)} 期)，可能存在网络问题")
        
        return self.lottery_data
    
    def _parse_number(self, text):
        """解析数字，移除逗号等格式符号"""
        if not text or text == '-':
            return 0
        # 移除逗号、￥符号等
        cleaned = re.sub(r'[,￥¥元]', '', str(text))
        try:
            return int(float(cleaned))
        except:
            return 0
    
    def save_data(self, filename="data/lottery_data.json"):
        """保存数据到文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.lottery_data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")
    
    def load_data(self, filename="data/lottery_data.json"):
        """从文件加载数据"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.lottery_data = json.load(f)
            print(f"从 {filename} 加载了 {len(self.lottery_data)} 期数据")
            return True
        except FileNotFoundError:
            print(f"文件 {filename} 不存在")
            return False
        except json.JSONDecodeError:
            print(f"文件 {filename} 内容解析失败")
            return False

    def fetch_lottery_data_incremental(self, start_date, end_date=None):
        """
        增量抓取双色球数据：
        - start_date: 字符串 'YYYY-MM-DD'，从该日期开始（含）抓取
        - end_date: 字符串 'YYYY-MM-DD'，默认到当前日期
        
        说明：
        - 在已有历史数据基础上，仅补充 start_date 之后的新数据，避免重复抓取全部历史。
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        print(f"\n开始增量抓取双色球数据：从 {start_date} 到 {end_date}")
        
        new_records = []
        consecutive_failures = 0
        max_consecutive_failures = 5
        page = 1

        while True:
            print(f"📄 增量抓取第 {page} 页数据...")

            max_retries = 5
            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    # 每页或重试时更新headers
                    if page == 1 or retry_count > 0:
                        self._update_headers()

                    params = {
                        'name': 'ssq',
                        'pageNo': page,
                        'pageSize': 30,
                        'systemType': 'PC',
                        'dayStart': start_date,
                        'dayEnd': end_date
                    }

                    print(f"🌐 发送增量请求到API... (页面 {page}, 尝试 {retry_count + 1})")
                    response = self.session.get(self.api_url, params=params, timeout=30)

                    print(f"📡 响应状态码: {response.status_code}")
                    response.raise_for_status()

                    data = response.json()
                    print(f"📊 API响应解析: state={data.get('state')}")

                    if data.get('state') != 0:
                        print(f"❌ API返回错误: {data.get('message', '未知错误')}")
                        retry_count += 1
                        continue

                    results = data.get('result', [])
                    if not results:
                        print(f"📭 增量抓取第 {page} 页无数据，结束。")
                        success = True
                        break

                    print(f"✅ 第 {page} 页获取到 {len(results)} 条记录")
                    consecutive_failures = 0

                    for item in results:
                        try:
                            period = item.get('code', '')
                            date_str = item.get('date', '')
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
                            if not date_match:
                                continue
                            draw_date = date_match.group(1)

                            # 只保留 >= start_date 的记录（防御性过滤）
                            if draw_date < start_date:
                                continue

                            red_str = item.get('red', '')
                            if not red_str:
                                continue
                            red_balls = [int(x.strip()) for x in red_str.split(',')]

                            blue_str = item.get('blue', '')
                            if not blue_str:
                                continue
                            blue_ball = int(blue_str)

                            sales_amount = self._parse_number(item.get('sales', '0'))
                            pool_amount = self._parse_number(item.get('poolmoney', '0'))

                            prizegrades = item.get('prizegrades', [])
                            first_prize_count = 0
                            first_prize_amount = 0
                            second_prize_count = 0
                            second_prize_amount = 0

                            for grade in prizegrades:
                                if grade.get('type') == 1:
                                    first_prize_count = self._parse_number(grade.get('typenum', '0'))
                                    first_prize_amount = self._parse_number(grade.get('typemoney', '0'))
                                elif grade.get('type') == 2:
                                    second_prize_count = self._parse_number(grade.get('typenum', '0'))
                                    second_prize_amount = self._parse_number(grade.get('typemoney', '0'))

                            lottery_record = {
                                'period': period,
                                'date': draw_date,
                                'red_balls': red_balls,
                                'blue_ball': blue_ball,
                                'first_prize_count': first_prize_count,
                                'first_prize_amount': first_prize_amount,
                                'second_prize_count': second_prize_count,
                                'second_prize_amount': second_prize_amount,
                                'sales_amount': sales_amount,
                                'pool_amount': pool_amount
                            }

                            new_records.append(lottery_record)

                        except Exception as e:
                            print(f"⚠️  解析增量记录时出错: {e}")
                            continue

                    success = True

                except requests.exceptions.Timeout:
                    print(f"⏰ 增量抓取网络超时 (页面 {page}, 尝试 {retry_count + 1})")
                    retry_count += 1
                except requests.exceptions.ConnectionError:
                    print(f"🔌 增量抓取连接错误 (页面 {page}, 尝试 {retry_count + 1})")
                    retry_count += 1
                except requests.exceptions.HTTPError as e:
                    print(f"🌐 增量抓取HTTP错误: {e} (页面 {page}, 尝试 {retry_count + 1})")
                    retry_count += 1
                except Exception as e:
                    print(f"❌ 增量抓取第 {page} 页时出错: {e} (尝试 {retry_count + 1})")
                    retry_count += 1

                if retry_count >= max_retries:
                    consecutive_failures += 1
                    print(f"💥 增量抓取第 {page} 页重试 {max_retries} 次后仍然失败，跳过此页")
                    break

            if not success or consecutive_failures >= max_consecutive_failures:
                if consecutive_failures >= max_consecutive_failures:
                    print(f"🛑 增量抓取连续 {max_consecutive_failures} 页失败，停止抓取以避免被封禁")
                break

            # 如果本页数据条数少于 pageSize，说明已经到末尾
            if len(results) < 30:
                break

            page += 1

        if not new_records:
            print("📭 本次增量抓取没有发现新数据。")
            return 0

        # 将新纪录与现有数据合并，按期号排序去重（期号越大越新）
        print(f"🎉 增量抓取完成，共获取 {len(new_records)} 期新数据，开始合并去重...")
        # 现有数据 + 新数据 合并
        all_records = {rec['period']: rec for rec in self.lottery_data}
        for rec in new_records:
            all_records[rec['period']] = rec

        # 期号按字符串排序即可（格式为YYYYNNN），从新到旧
        sorted_periods = sorted(all_records.keys(), reverse=True)
        self.lottery_data = [all_records[p] for p in sorted_periods]

        print(f"✅ 合并后总共有 {len(self.lottery_data)} 期数据")
        return len(new_records)

    def init_and_update_history(
        self,
        data_path: str = "data/lottery_data.json",
        backup_path: str = "data/initial_backup/lottery_data_initial.json"
    ):
        """
        初始化并增量更新历史数据，逻辑：
        1. 优先从 data_path 读取主数据；
        2. 若主数据不存在或为空，则尝试从 backup_path 读取初始备份数据；
        3. 若仍失败，则从最早历史完整抓取一次，并同时写入主数据和初始备份；
        4. 在已有历史数据基础上，根据最新日期做增量抓取，仅补充新期数。
        
        注：初始备份只在“首次完整抓取”时写一次，后续不再覆盖，节约资源。
        """
        print("\n=== 初始化并增量更新双色球历史数据 ===")

        # 1. 尝试读取主数据
        data_loaded = self.load_data(data_path)
        if not data_loaded or not self.lottery_data:
            print("主数据读取失败或为空，尝试从初始备份读取...")
            # 2. 尝试读取初始备份
            backup_loaded = self.load_data(backup_path)
            if backup_loaded and self.lottery_data:
                print(f"✅ 已从初始备份 {backup_path} 载入历史数据，将其保存为主数据。")
                self.save_data(data_path)
            else:
                print("初始备份读取失败或为空，将从最早历史开始完整抓取一次...")
                # 3. 完整抓取一次历史数据
                max_pages = self.get_max_pages()
                self.fetch_lottery_data(max_pages=max_pages)
                if not self.lottery_data:
                    print("❌ 完整抓取历史数据失败，无法继续。")
                    return
                # 保存主数据
                self.save_data(data_path)
                # 写入初始备份（只在首次完整抓取时写一次）
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                print(f"🔄 正在写入初始备份数据到 {backup_path}")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(self.lottery_data, f, ensure_ascii=False, indent=2)
                print("✅ 初始备份写入完成。")

        if not self.lottery_data:
            print("❌ 无可用历史数据，跳过增量更新。")
            return

        # 4. 基于已有历史做增量抓取
        # 假设 self.lottery_data 已按期号从新到旧排序（现有抓取逻辑就是这样）
        latest_record = self.lottery_data[0]
        latest_date_str = latest_record.get('date')
        print(f"当前历史数据最新一期: 期号 {latest_record.get('period')} 日期 {latest_date_str}")

        try:
            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
        except Exception:
            print("⚠️ 最新日期字段格式异常，跳过增量抓取。")
            return

        next_day = latest_date + timedelta(days=1)
        today = datetime.now()

        if next_day.date() > today.date():
            print("📭 历史数据已是最新，无需增量抓取。")
            return

        start_date = next_day.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')

        new_count = self.fetch_lottery_data_incremental(start_date=start_date, end_date=end_date)
        if new_count > 0:
            # 更新主数据
            self.save_data(data_path)
        else:
            print("📭 没有新增期数，无需保存主数据。")
    
    def analyze_frequency(self):
        """分析号码出现频率"""
        print("\n=== 号码频率分析 ===")
        
        # 红球频率分析
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in self.lottery_data:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        # 红球频率排序
        red_freq = sorted(red_counter.items(), key=lambda x: x[1], reverse=True)
        print("\n红球出现频率排行榜（前10）：")
        for i, (num, count) in enumerate(red_freq[:10], 1):
            percentage = (count / len(self.lottery_data)) * 100
            print(f"{i:2d}. 号码 {num:2d}: 出现 {count:3d} 次 ({percentage:.1f}%)")
        
        # 蓝球频率排序
        blue_freq = sorted(blue_counter.items(), key=lambda x: x[1], reverse=True)
        print("\n蓝球出现频率排行榜（前10）：")
        for i, (num, count) in enumerate(blue_freq[:10], 1):
            percentage = (count / len(self.lottery_data)) * 100
            print(f"{i:2d}. 号码 {num:2d}: 出现 {count:3d} 次 ({percentage:.1f}%)")
        
        return red_counter, blue_counter
    
    def analyze_patterns(self):
        """分析号码规律"""
        print("\n=== 号码规律分析 ===")
        
        # 奇偶分布分析
        odd_even_dist = defaultdict(int)
        sum_dist = defaultdict(int)
        span_dist = defaultdict(int)
        
        for record in self.lottery_data:
            red_balls = record['red_balls']
            
            # 奇偶分析
            odd_count = sum(1 for x in red_balls if x % 2 == 1)
            even_count = 6 - odd_count
            odd_even_dist[f"{odd_count}奇{even_count}偶"] += 1
            
            # 和值分析
            total_sum = sum(red_balls)
            sum_range = f"{(total_sum//10)*10}-{(total_sum//10)*10+9}"
            sum_dist[sum_range] += 1
            
            # 跨度分析
            span = max(red_balls) - min(red_balls)
            span_range = f"{(span//5)*5}-{(span//5)*5+4}"
            span_dist[span_range] += 1
        
        print("\n奇偶分布统计：")
        for pattern, count in sorted(odd_even_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.lottery_data)) * 100
            print(f"{pattern}: {count} 次 ({percentage:.1f}%)")
        
        print("\n和值分布统计：")
        for sum_range, count in sorted(sum_dist.items(), key=lambda x: int(x[0].split('-')[0])):
            percentage = (count / len(self.lottery_data)) * 100
            print(f"{sum_range}: {count} 次 ({percentage:.1f}%)")
        
        print("\n跨度分布统计：")
        for span_range, count in sorted(span_dist.items(), key=lambda x: int(x[0].split('-')[0])):
            percentage = (count / len(self.lottery_data)) * 100
            print(f"{span_range}: {count} 次 ({percentage:.1f}%)")
    
    def analyze_trends(self):
        """分析走势"""
        print("\n=== 走势分析 ===")
        
        if len(self.lottery_data) < 10:
            print("数据不足，无法进行走势分析")
            return
        
        # 最近10期的号码
        recent_10 = self.lottery_data[:10]
        
        print("最近10期开奖号码：")
        for record in recent_10:
            red_str = " ".join([f"{x:2d}" for x in record['red_balls']])
            print(f"{record['period']}: {red_str} + {record['blue_ball']:2d}")
        
        # 冷热号分析
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in recent_10:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        print(f"\n最近10期红球热号（出现2次及以上）：")
        hot_reds = [num for num, count in red_counter.items() if count >= 2]
        if hot_reds:
            hot_reds.sort()
            print(" ".join([f"{x:2d}" for x in hot_reds]))
        else:
            print("无")
        
        print(f"\n最近10期蓝球热号（出现2次及以上）：")
        hot_blues = [num for num, count in blue_counter.items() if count >= 2]
        if hot_blues:
            hot_blues.sort()
            print(" ".join([f"{x:2d}" for x in hot_blues]))
        else:
            print("无")
    
    def generate_recommendations(self, num_sets=5):
        """生成推荐号码（基于智能分析的动态推荐）"""
        print(f"\n=== 生成 {num_sets} 组推荐号码 ===")
        
        if not self.lottery_data:
            print("无数据，无法生成推荐")
            return []
        
        # 统计频率
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in self.lottery_data:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        # 确保所有红球都有记录（即使频率为0）
        for i in range(1, 34):
            if i not in red_counter:
                red_counter[i] = 0
                
        # 确保所有蓝球都有记录
        for i in range(1, 17):
            if i not in blue_counter:
                blue_counter[i] = 0
        
        # 获取红球频率排序
        red_freq_sorted = sorted(red_counter.items(), key=lambda x: x[1], reverse=True)
        blue_freq_sorted = sorted(blue_counter.items(), key=lambda x: x[1], reverse=True)
        
        # 分层分组：高频、中频、低频
        total_reds = len(red_freq_sorted)
        high_cutoff = max(6, total_reds // 3)  # 至少6个高频球
        mid_cutoff = max(12, 2 * total_reds // 3)  # 至少12个中频球
        
        high_freq_reds = [num for num, _ in red_freq_sorted[:high_cutoff]]
        mid_freq_reds = [num for num, _ in red_freq_sorted[high_cutoff:mid_cutoff]]
        low_freq_reds = [num for num, _ in red_freq_sorted[mid_cutoff:]]
        
        # 获取高频蓝球
        high_freq_blues = [num for num, _ in blue_freq_sorted[:8]]
        
        print(f"高频红球({len(high_freq_reds)}个): {sorted(high_freq_reds)}")
        print(f"中频红球({len(mid_freq_reds)}个): {sorted(mid_freq_reds)}")
        print(f"低频红球({len(low_freq_reds)}个): {sorted(low_freq_reds)}")
        print(f"高频蓝球: {sorted(high_freq_blues)}")
        
        recommendations = []
        
        # 定义多种智能选号策略
        strategies = [
            {
                'name': '高频主导',
                'high': 4, 'mid': 2, 'low': 0,
                'blue_rank': 0,
                'description': '基于最高频号码的稳定组合'
            },
            {
                'name': '均衡分布', 
                'high': 3, 'mid': 2, 'low': 1,
                'blue_rank': 1,
                'description': '高中低频均衡的平衡组合'
            },
            {
                'name': '中频优先',
                'high': 2, 'mid': 3, 'low': 1, 
                'blue_rank': 2,
                'description': '中频主导的稳健组合'
            },
            {
                'name': '冷热结合',
                'high': 3, 'mid': 1, 'low': 2,
                'blue_rank': 3,
                'description': '热号与冷号结合的对冲组合'
            },
            {
                'name': '超高频',
                'high': 5, 'mid': 1, 'low': 0,
                'blue_rank': 0,
                'description': '超高频号码的激进组合'
            },
            {
                'name': '低频反选',
                'high': 1, 'mid': 2, 'low': 3,
                'blue_rank': 4,
                'description': '低频号码的反向思维组合'
            },
            {
                'name': '随机均衡',
                'high': 2, 'mid': 2, 'low': 2,
                'blue_rank': 2,
                'description': '各频段随机均衡组合'
            },
            {
                'name': '奇偶优化',
                'high': 3, 'mid': 2, 'low': 1,
                'blue_rank': 1,
                'description': '考虑奇偶平衡的优化组合'
            }
        ]
        
        random.seed(42)  # 固定种子，确保结果可重现
        
        for i, strategy in enumerate(strategies[:num_sets]):
            selected_reds = []
            
            # 从各频段选择号码
            pools = [
                (high_freq_reds, strategy['high']),
                (mid_freq_reds, strategy['mid']),
                (low_freq_reds, strategy['low'])
            ]
            
            for pool, count in pools:
                if count > 0 and pool:
                    # 确保不超出池子大小
                    actual_count = min(count, len(pool))
                    # 从池子中随机选择（但基于策略偏好）
                    if len(pool) >= actual_count:
                        if strategy['name'] == '奇偶优化':
                            # 特殊处理：优先保证奇偶平衡
                            selected_from_pool = self._select_with_odd_even_balance(pool, actual_count, selected_reds)
                        else:
                            selected_from_pool = random.sample(pool, actual_count)
                        selected_reds.extend(selected_from_pool)
            
            # 确保有6个红球
            while len(selected_reds) < 6:
                all_available = set(high_freq_reds + mid_freq_reds + low_freq_reds) - set(selected_reds)
                if all_available:
                    selected_reds.append(random.choice(list(all_available)))
                else:
                    # 如果所有球都用完了，从1-33中补充
                    remaining = set(range(1, 34)) - set(selected_reds)
                    if remaining:
                        selected_reds.append(random.choice(list(remaining)))
                    else:
                        break
            
            # 只保留前6个
            selected_reds = sorted(selected_reds[:6])
            
            # 选择蓝球
            blue_rank = strategy['blue_rank']
            if blue_rank < len(high_freq_blues):
                selected_blue = high_freq_blues[blue_rank]
            else:
                selected_blue = high_freq_blues[0] if high_freq_blues else 1
            
            # 计算组合特征
            odd_count = sum(1 for x in selected_reds if x % 2 == 1)
            even_count = 6 - odd_count
            total_sum = sum(selected_reds)
            span = max(selected_reds) - min(selected_reds)
            
            # 计算频率得分
            red_total_freq = sum(red_counter.get(red, 0) for red in selected_reds)
            blue_freq = blue_counter.get(selected_blue, 0)
            
            # 计算和值和跨度所属区间（与规律分析保持一致）
            sum_range = f"{(total_sum//10)*10}-{(total_sum//10)*10+9}"
            span_range = f"{(span//5)*5}-{(span//5)*5+4}"

            recommendations.append({
                'red_balls': selected_reds,
                'blue_ball': selected_blue,
                'description': strategy['description'],
                'strategy': strategy['name'],
                'odd_even': f"{odd_count}奇{even_count}偶",
                'sum': total_sum,
                'sum_range': sum_range,
                'span': span,
                'span_range': span_range,
                'red_freq_sum': red_total_freq,
                'blue_freq': blue_freq
            })
        
        print("\n基于智能策略的推荐号码：")
        for i, rec in enumerate(recommendations, 1):
            red_str = " ".join([f"{x:02d}" for x in rec['red_balls']])
            print(f"推荐 {i}: {red_str} + {rec['blue_ball']:02d}")
            print(f"       策略: {rec['strategy']} | {rec['odd_even']} | 和值:{rec['sum']} | 跨度:{rec['span']}")
            print(f"       说明: {rec['description']}")
        
        return recommendations
    
    def _get_zone_index(self, num):
        """根据红球号码获取所属分区索引（0-6，对应1-5,6-10,...,31-33）"""
        if 1 <= num <= 5:
            return 0
        if 6 <= num <= 10:
            return 1
        if 11 <= num <= 15:
            return 2
        if 16 <= num <= 20:
            return 3
        if 21 <= num <= 25:
            return 4
        if 26 <= num <= 30:
            return 5
        return 6  # 31-33
    
    def _get_zone_pattern(self, red_balls):
        """获取红球在7个分区上的分布模式，用于覆盖优化"""
        zones = [0] * 7
        for n in red_balls:
            idx = self._get_zone_index(n)
            zones[idx] += 1
        # 生成类似 "1-0-2-1-1-0-1" 的字符串
        return "-".join(str(x) for x in zones)
    
    def generate_coverage_optimized_recommendations(self, total_sets=20, candidate_multiplier=8):
        """
        生成覆盖优化后的推荐号码组合
        
        目标：在相同注数预算下，让号码组合在奇偶、和值、分区等维度上更加分散，
        从而让中小奖（部分命中）的体验更稳定，而不是追求提高理论中奖概率。
        """
        print(f"\n=== 覆盖优化推荐：目标组合数 {total_sets} 组 ===")
        
        if not self.lottery_data:
            print("无数据，无法生成覆盖优化推荐")
            return []
        
        # 先基于历史数据做频率分析，构造候选空间
        red_counter = Counter()
        blue_counter = Counter()
        for record in self.lottery_data:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        for i in range(1, 34):
            red_counter.setdefault(i, 0)
        for i in range(1, 17):
            blue_counter.setdefault(i, 0)
        
        red_freq_sorted = sorted(red_counter.items(), key=lambda x: x[1], reverse=True)
        blue_freq_sorted = sorted(blue_counter.items(), key=lambda x: x[1], reverse=True)
        
        total_reds = len(red_freq_sorted)
        high_cutoff = max(6, total_reds // 3)
        mid_cutoff = max(12, 2 * total_reds // 3)
        
        high_freq_reds = [num for num, _ in red_freq_sorted[:high_cutoff]]
        mid_freq_reds = [num for num, _ in red_freq_sorted[high_cutoff:mid_cutoff]]
        low_freq_reds = [num for num, _ in red_freq_sorted[mid_cutoff:]]
        high_freq_blues = [num for num, _ in blue_freq_sorted[:8]] or list(range(1, 17))
        
        print(f"覆盖优化使用的高频红球池: {sorted(high_freq_reds)}")
        print(f"覆盖优化使用的中频红球池: {sorted(mid_freq_reds)}")
        print(f"覆盖优化使用的低频红球池: {sorted(low_freq_reds)}")
        
        # 简单策略：偏高频 + 中频 + 少量低频，兼顾冷热
        base_strategy = {'high': 3, 'mid': 2, 'low': 1}
        
        # 生成候选组合池（数量为目标组合数的 candidate_multiplier 倍）
        target_candidates = max(total_sets * candidate_multiplier, total_sets * 3)
        random.seed(12345)  # 与普通推荐分开，保证可复现
        
        candidates = []
        seen_combos = set()
        
        def build_one_combo():
            reds = []
            pools = [
                (high_freq_reds, base_strategy['high']),
                (mid_freq_reds, base_strategy['mid']),
                (low_freq_reds, base_strategy['low']),
            ]
            for pool, cnt in pools:
                if cnt > 0 and pool:
                    k = min(cnt, len(pool))
                    reds.extend(random.sample(pool, k))
            # 补齐到6个红球
            while len(reds) < 6:
                all_available = set(range(1, 34)) - set(reds)
                if not all_available:
                    break
                reds.append(random.choice(list(all_available)))
            reds = tuple(sorted(reds[:6]))
            
            # 蓝球：优先从高频中选，其次全局随机
            if high_freq_blues:
                if random.random() < 0.7:
                    blue = random.choice(high_freq_blues)
                else:
                    blue = random.randint(1, 16)
            else:
                blue = random.randint(1, 16)
            return reds, blue
        
        while len(candidates) < target_candidates:
            reds, blue = build_one_combo()
            key = (reds, blue)
            if key in seen_combos:
                continue
            seen_combos.add(key)
            
            odd_count = sum(1 for x in reds if x % 2 == 1)
            even_count = 6 - odd_count
            total_sum = sum(reds)
            sum_range = f"{(total_sum//10)*10}-{(total_sum//10)*10+9}"
            span = max(reds) - min(reds)
            zone_pattern = self._get_zone_pattern(reds)
            red_total_freq = sum(red_counter.get(r, 0) for r in reds)
            blue_freq = blue_counter.get(blue, 0)
            
            candidates.append({
                'red_balls': list(reds),
                'blue_ball': blue,
                'odd_even': f"{odd_count}奇{even_count}偶",
                'sum': total_sum,
                'sum_range': sum_range,
                'span': span,
                'zone_pattern': zone_pattern,
                'red_freq_sum': red_total_freq,
                'blue_freq': blue_freq,
            })
        
        print(f"已生成候选组合 {len(candidates)} 组，开始执行覆盖优化选择...")
        
        # 覆盖优化：贪心选择，控制组合相似度，并平衡奇偶/和值/分区分布
        selected = []
        odd_even_usage = Counter()
        sum_range_usage = Counter()
        zone_pattern_usage = Counter()
        
        def overlap_penalty(candidate):
            """与已选组合的最大红球重合数，越小越好"""
            if not selected:
                return 0
            reds = set(candidate['red_balls'])
            return max(len(reds & set(s['red_balls'])) for s in selected)
        
        while len(selected) < total_sets and candidates:
            # 计算每个候选的评分
            best_idx = None
            best_key = None
            
            for idx, c in enumerate(candidates):
                ov = overlap_penalty(c)
                # 强约束：不接受与已有组合红球重合 >=5 的候选，避免组合高度类似
                if ov >= 5:
                    continue
                
                usage_score = (
                    odd_even_usage[c['odd_even']] +
                    sum_range_usage[c['sum_range']] +
                    zone_pattern_usage[c['zone_pattern']]
                )
                # 频率得分：偏向整体历史频率略高的组合，但权重很小
                freq_score = c['red_freq_sum'] + c['blue_freq']
                # 排序键：先最小重合，其次最小使用度，最后最大频率
                key = (ov, usage_score, -freq_score)
                
                if best_key is None or key < best_key:
                    best_key = key
                    best_idx = idx
            
            if best_idx is None:
                # 剩余候选都过于相似，直接退出
                break
            
            chosen = candidates.pop(best_idx)
            selected.append(chosen)
            odd_even_usage[chosen['odd_even']] += 1
            sum_range_usage[chosen['sum_range']] += 1
            zone_pattern_usage[chosen['zone_pattern']] += 1
        
        print(f"覆盖优化完成，最终选择 {len(selected)} 组组合。")
        print("覆盖优化推荐号码：")
        for i, rec in enumerate(selected, 1):
            red_str = " ".join([f"{x:2d}" for x in rec['red_balls']])
            print(f"推荐 {i}: {red_str} + {rec['blue_ball']:2d}")
            print(f"       特征: {rec['odd_even']} | 和值:{rec['sum']} | 跨度:{rec['span']} | 分区:{rec['zone_pattern']}")
        
        # 为了与原有结构兼容，补充描述字段
        for rec in selected:
            rec.setdefault('description', '覆盖优化组合（分散奇偶、和值和分区分布）')
            rec.setdefault('strategy', '覆盖优化')
        
        return selected

    def generate_betting_plan_for_7_tickets(self):
        """
        生成一套符合以下结构的投注方案：
        - 5 注：标准 6+1 单式票
        - 1 注：7+1 复式票
        - 1 注：6+2 复式票
        
        目标依旧是：在固定预算下，尽量分散号码，提升中小奖体验的稳定性。
        """
        print("\n=== 生成 7 注结构化投注方案 ===")
        if not self.lottery_data:
            print("无数据，无法生成投注方案")
            return {}

        # 先用覆盖优化生成基础候选组合（至少 7 组）
        coverage_recs = self.generate_coverage_optimized_recommendations(total_sets=7)
        if len(coverage_recs) < 3:
            print("覆盖优化组合数量不足，无法构造完整方案")
            return {}

        # 统计历史频率（用于挑选蓝球等）
        red_counter = Counter()
        blue_counter = Counter()
        for record in self.lottery_data:
            for r in record['red_balls']:
                red_counter[r] += 1
            blue_counter[record['blue_ball']] += 1

        # ---------- 1. 5 注 6+1 单式 ----------
        single_tickets = []
        for rec in coverage_recs[:5]:
            single_tickets.append({
                "red_balls": sorted(rec["red_balls"]),
                "blue_balls": [rec["blue_ball"]],
                "type": "6+1",
                "source_strategy": rec.get("strategy", "覆盖优化")
            })

        # ---------- 2. 1 注 7+1 复式 ----------
        # 思路：在已选组合的基础上，尽量扩展到 7 个不重复红球，蓝球选高频蓝之一
        all_reds = set()
        for rec in coverage_recs:
            all_reds.update(rec["red_balls"])
        all_reds = sorted(all_reds)

        if len(all_reds) >= 7:
            reds_7 = all_reds[:7]
        else:
            # 不足 7 个则从全局补齐
            reds_7 = list(all_reds)
            for n in range(1, 34):
                if n not in reds_7:
                    reds_7.append(n)
                if len(reds_7) >= 7:
                    break

        # 选择一个较高频的蓝球作为 7+1 的蓝球
        if blue_counter:
            most_common_blues = sorted(blue_counter.items(), key=lambda x: x[1], reverse=True)
            blue_for_7_1 = most_common_blues[0][0]
        else:
            # 退化情况，直接取覆盖推荐的第一个蓝球
            blue_for_7_1 = coverage_recs[0]["blue_ball"]

        ticket_7_1 = {
            "red_balls": sorted(reds_7),
            "blue_balls": [blue_for_7_1],
            "type": "7+1",
            "description": "基于覆盖优化结果扩展到 7 个红球，作为复式覆盖"
        }

        # ---------- 3. 1 注 6+2 复式 ----------
        # 思路：选一组代表性红球 + 2 个尽量不同的高频蓝球
        base_reds_for_6_2 = sorted(coverage_recs[5]["red_balls"])

        # 获取按频率排序的蓝球列表
        if blue_counter:
            sorted_blues = [b for b, _ in sorted(blue_counter.items(), key=lambda x: x[1], reverse=True)]
        else:
            sorted_blues = list(range(1, 17))

        blue_for_6_2 = []
        for b in sorted_blues:
            if b not in blue_for_6_2:
                blue_for_6_2.append(b)
            if len(blue_for_6_2) >= 2:
                break

        ticket_6_2 = {
            "red_balls": base_reds_for_6_2,
            "blue_balls": blue_for_6_2,
            "type": "6+2",
            "description": "使用覆盖优化红球 + 2 个高频蓝球构建复式"
        }

        betting_plan = {
            "singles_6_1": single_tickets,
            "combo_7_1": ticket_7_1,
            "combo_6_2": ticket_6_2
        }

        # 打印方案概览
        print("\n--- 5 注 6+1 单式 ---")
        for i, t in enumerate(single_tickets, 1):
            red_str = " ".join(f"{x:02d}" for x in t["red_balls"])
            blue_str = " ".join(f"{x:02d}" for x in t["blue_balls"])
            print(f"单式 {i}: {red_str} + {blue_str}  (策略: {t['source_strategy']})")

        print("\n--- 1 注 7+1 复式 ---")
        red_str = " ".join(f"{x:02d}" for x in ticket_7_1["red_balls"])
        blue_str = " ".join(f"{x:02d}" for x in ticket_7_1["blue_balls"])
        print(f"7+1: {red_str} + {blue_str}")

        print("\n--- 1 注 6+2 复式 ---")
        red_str = " ".join(f"{x:02d}" for x in ticket_6_2["red_balls"])
        blue_str = " ".join(f"{x:02d}" for x in ticket_6_2["blue_balls"])
        print(f"6+2: {red_str} + {blue_str}")

        print("\n✅ 7 注投注方案生成完成（目标：在固定预算下分散风险、平滑中小奖体验）。")

        return betting_plan

    def generate_enhanced_plan_with_combos(self, recommendations=None, red_dan=None, blue_dan=None, silent=False):
        """
        基于8种智能策略推荐 + 历史规律分析，生成：
        - 8 注 6+1 单式（原有8种策略）
        - 1 注 7+1 复式
        - 1 注 6+2 复式
        
        复式采用价值回归思路：7+1、6+2 基于“历史最低匹配”策略构建，
        扩展球选用历史低频号码，期待冷门特征回归。
        """
        if not silent:
            print("\n=== 生成增强版推荐方案：8种策略 + 2种复式 ===")
        if not self.lottery_data:
            if not silent:
                print("无数据，无法生成推荐方案")
            return {}

        # 历史规律原始分布（奇偶 / 和值区间 / 跨度区间）
        patterns_raw = self._get_patterns_analysis_raw()
        odd_even_dist = patterns_raw.get('odd_even_dist', {})
        sum_dist = patterns_raw.get('sum_dist', {})
        span_dist = patterns_raw.get('span_dist', {})

        # 先生成8种策略推荐（6+1 单式），或复用外部传入的结果
        if recommendations is None:
            recommendations = self.generate_recommendations(num_sets=8)
        if not recommendations:
            if not silent:
                print("8种策略推荐生成失败，无法构建增强方案。")
            return {}

        # 分析每种策略在历史中的“支持度”：奇偶/和值/跨度在历史中的出现次数
        # 价值回归：复式选用历史最低匹配策略（得分最低），期待冷门特征回归
        best_rec = None
        best_score = None
        for rec in recommendations:
            oe = rec.get('odd_even')
            sr = rec.get('sum_range')
            sp = rec.get('span_range')
            score = (
                odd_even_dist.get(oe, 0) +
                sum_dist.get(sr, 0) +
                span_dist.get(sp, 0)
            )
            rec['history_score'] = score
            if best_score is None or score < best_score:
                best_score = score
                best_rec = rec

        if not silent:
            print("\n历史匹配度评分（越低表示该策略特征在历史中越少见，复式采用最低分策略）：")
            for idx, rec in enumerate(recommendations, 1):
                print(f"策略 {idx} [{rec['strategy']}]: 历史匹配得分 = {rec.get('history_score', 0)}")

        if not best_rec:
            if not silent:
                print("未能根据历史数据识别出策略特征，跳过复式构建。")
            best_rec = recommendations[0]

        if not silent:
            print(f"\n📌 复式采用历史最低匹配策略（价值回归）: {best_rec['strategy']} (得分 {best_rec.get('history_score', 0)})")

        # ---------- 8 注 6+1 单式（直接使用8种策略结果） ----------
        singles_6_1 = []
        for rec in recommendations:
            singles_6_1.append({
                "red_balls": sorted(rec["red_balls"]),
                "blue_balls": [rec["blue_ball"]],
                "type": "6+1",
                "strategy": rec["strategy"],
                "description": rec["description"],
                "odd_even": rec["odd_even"],
                "sum": rec["sum"],
                "span": rec["span"]
            })

        # ---------- 构建复式使用的基础信息 ----------
        # 历史频率统计，用于选额外红球/蓝球
        red_counter = Counter()
        blue_counter = Counter()
        for record in self.lottery_data:
            for r in record['red_balls']:
                red_counter[r] += 1
            blue_counter[record['blue_ball']] += 1

        # 以历史最低匹配策略（价值回归）的红球为基础
        base_reds = sorted(best_rec["red_balls"])
        base_blue = best_rec["blue_ball"]

        # 如果传入了红胆/蓝胆参数，则进行约束：确保这些号码被包含进基础组合
        if red_dan:
            red_dan_set = {int(x) for x in red_dan if 1 <= int(x) <= 33}
            # 先把胆号全部加进去
            for d in red_dan_set:
                if d not in base_reds:
                    base_reds.append(d)
            base_reds = sorted(base_reds)
            # 如果超过6个，则优先保留胆号，再根据历史频率剔除非胆号中频率最低的，直到只剩6个
            if len(base_reds) > 6:
                non_dan = [n for n in base_reds if n not in red_dan_set]
                # 按历史频率升序排序，优先剔除低频的
                non_dan_sorted = sorted(non_dan, key=lambda n: red_counter.get(n, 0))
                while len(base_reds) > 6 and non_dan_sorted:
                    to_remove = non_dan_sorted.pop(0)
                    if to_remove in base_reds:
                        base_reds.remove(to_remove)

        if blue_dan:
            # 取第一个合法的蓝胆作为基础蓝球
            for b in blue_dan:
                b_int = int(b)
                if 1 <= b_int <= 16:
                    base_blue = b_int
                    break

        # ---------- 7+1 复式：在基础6个红球上扩展1个红球 ----------
        # 价值回归：选择历史低频、且不在基础组合中的一个红球作为扩展
        extra_red = None
        if red_counter:
            sorted_reds_by_freq = [n for n, _ in sorted(red_counter.items(), key=lambda x: x[1])]
            for n in sorted_reds_by_freq:
                if n not in base_reds:
                    extra_red = n
                    break
        if extra_red is None:
            # 退化情况：从1-33中随便补一个没出现的
            for n in range(1, 34):
                if n not in base_reds:
                    extra_red = n
                    break
        if extra_red is None:
            # 所有号都在基础组合里（理论上不会发生），就重复使用基础中的一个
            extra_red = base_reds[0]

        reds_7_1 = sorted(base_reds + [extra_red])
        ticket_7_1 = {
            "red_balls": reds_7_1,
            "blue_balls": [base_blue],
            "type": "7+1",
            "source_strategy": best_rec["strategy"],
            "description": "基于历史最低匹配策略（价值回归）扩展1个低频红球构建7+1复式"
        }

        # ---------- 6+2 复式：基础红球 + 1个额外蓝球 ----------
        # 价值回归：选择一个与基础蓝球不同的低频蓝球
        extra_blue = None
        if blue_counter:
            sorted_blues_by_freq = [b for b, _ in sorted(blue_counter.items(), key=lambda x: x[1])]
            for b in sorted_blues_by_freq:
                if b != base_blue:
                    extra_blue = b
                    break
        if extra_blue is None:
            # 退化情况：从1-16中选一个不同的
            for b in range(1, 17):
                if b != base_blue:
                    extra_blue = b
                    break
        if extra_blue is None:
            extra_blue = base_blue

        ticket_6_2 = {
            "red_balls": base_reds,
            "blue_balls": sorted([base_blue, extra_blue]),
            "type": "6+2",
            "source_strategy": best_rec["strategy"],
            "description": "基于历史最低匹配策略（价值回归）蓝球扩展构建6+2复式"
        }

        enhanced_plan = {
            "singles_6_1": singles_6_1,
            "combo_7_1": ticket_7_1,
            "combo_6_2": ticket_6_2
        }

        # 控制台输出总览（两位数格式）
        if not silent:
            print("\n--- 8 注 6+1 单式（智能策略） ---")
            for i, t in enumerate(singles_6_1, 1):
                red_str = " ".join(f"{x:02d}" for x in t["red_balls"])
                blue_str = " ".join(f"{x:02d}" for x in t["blue_balls"])
                print(f"单式 {i}: {red_str} + {blue_str}  (策略: {t['strategy']})")

            print("\n--- 1 注 7+1 复式（基于历史最低匹配策略/价值回归） ---")
            red_str = " ".join(f"{x:02d}" for x in ticket_7_1["red_balls"])
            blue_str = " ".join(f"{x:02d}" for x in ticket_7_1["blue_balls"])
            print(f"7+1: {red_str} + {blue_str}  (来源策略: {ticket_7_1['source_strategy']})")

            print("\n--- 1 注 6+2 复式（基于历史最低匹配策略/价值回归） ---")
            red_str = " ".join(f"{x:02d}" for x in ticket_6_2["red_balls"])
            blue_str = " ".join(f"{x:02d}" for x in ticket_6_2["blue_balls"])
            print(f"6+2: {red_str} + {blue_str}  (来源策略: {ticket_6_2['source_strategy']})")

            print("\n✅ 增强版推荐方案生成完成：8种策略单式 + 7+1 + 6+2。")

        return enhanced_plan
    
    def _select_with_odd_even_balance(self, pool, count, existing_reds):
        """在选择时考虑奇偶平衡"""
        if count <= 0:
            return []
            
        existing_odd = sum(1 for x in existing_reds if x % 2 == 1)
        existing_even = len(existing_reds) - existing_odd
        
        # 目标：6个球中3-4个奇数比较平衡
        target_total_odd = 3 if len(existing_reds) + count <= 6 else 4
        needed_odd = max(0, target_total_odd - existing_odd)
        needed_even = count - needed_odd
        
        odd_pool = [x for x in pool if x % 2 == 1]
        even_pool = [x for x in pool if x % 2 == 0]
        
        selected = []
        
        # 选择奇数
        if needed_odd > 0 and odd_pool:
            actual_odd = min(needed_odd, len(odd_pool))
            selected.extend(random.sample(odd_pool, actual_odd))
        
        # 选择偶数
        if needed_even > 0 and even_pool:
            actual_even = min(needed_even, len(even_pool))
            selected.extend(random.sample(even_pool, actual_even))
        
        # 如果还不够，从剩余的球中补充
        while len(selected) < count and len(selected) < len(pool):
            remaining = [x for x in pool if x not in selected]
            if remaining:
                selected.append(random.choice(remaining))
            else:
                break
        
        return selected[:count]
    
    def visualize_frequency(self, save_plots=True):
        """可视化频率分析"""
        if not self.lottery_data:
            print("无数据，无法生成图表")
            return
        
        # 统计频率
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in self.lottery_data:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # 红球频率图
        red_nums = list(range(1, 34))
        red_freqs = [red_counter.get(num, 0) for num in red_nums]
        
        bars1 = ax1.bar(red_nums, red_freqs, color='red', alpha=0.7)
        ax1.set_title('红球出现频率分布', fontsize=16, fontweight='bold')
        ax1.set_xlabel('红球号码', fontsize=12)
        ax1.set_ylabel('出现次数', fontsize=12)
        ax1.set_xticks(red_nums)
        ax1.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, freq in zip(bars1, red_freqs):
            if freq > 0:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                        str(freq), ha='center', va='bottom', fontsize=8)
        
        # 蓝球频率图
        blue_nums = list(range(1, 17))
        blue_freqs = [blue_counter.get(num, 0) for num in blue_nums]
        
        bars2 = ax2.bar(blue_nums, blue_freqs, color='blue', alpha=0.7)
        ax2.set_title('蓝球出现频率分布', fontsize=16, fontweight='bold')
        ax2.set_xlabel('蓝球号码', fontsize=12)
        ax2.set_ylabel('出现次数', fontsize=12)
        ax2.set_xticks(blue_nums)
        ax2.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, freq in zip(bars2, blue_freqs):
            if freq > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                        str(freq), ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        if save_plots:
            # 确保目录存在
            os.makedirs('pics', exist_ok=True)
            plt.savefig('pics/lottery_frequency_analysis.png', dpi=300, bbox_inches='tight')
            print("频率分析图表已保存为 pics/lottery_frequency_analysis.png")
    
    def get_lottery_rules(self):
        """获取双色球游戏规则"""
        rules = """
        === 双色球游戏规则 ===
        
        1. 号码范围：
           - 红球：01-33，选择6个号码
           - 蓝球：01-16，选择1个号码
        
        2. 中奖等级：
           一等奖：6个红球 + 1个蓝球（浮动奖金，500万元起）
           二等奖：6个红球（浮动奖金）
           三等奖：5个红球 + 1个蓝球（固定3000元）
           四等奖：5个红球 或 4个红球 + 1个蓝球（固定200元）
           五等奖：4个红球 或 3个红球 + 1个蓝球（固定10元）
           六等奖：2个红球 + 1个蓝球 或 1个红球 + 1个蓝球 或 1个蓝球（固定5元）
        
        3. 开奖时间：每周二、四、日晚21:15
        
        4. 投注方式：
           - 单式投注：手动选择号码
           - 复式投注：选择7个以上红球进行组合
           - 机选投注：系统随机选择号码
        
        5. 中奖概率：
           一等奖：1/17,721,088
           二等奖：1/1,107,568
           三等奖：1/72,107
           
        注意：彩票投注有风险，请理性购彩，量力而行！
        """
        print(rules)
    
    def generate_analysis_report(self, filename="reports/analysis_report.md"):
        """生成完整的分析报告文件"""
        print(f"正在生成分析报告: {filename}")
        
        if not self.lottery_data:
            print("无数据，无法生成报告")
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # 执行所有分析
        red_counter, blue_counter = self._get_frequency_analysis()
        patterns_data = self._get_patterns_analysis()
        trends_data = self._get_trends_analysis()
        recommendations = self.generate_recommendations(num_sets=8)
        # 基于8种策略和历史规律生成增强版方案（8注6+1 + 7+1 + 6+2），静默模式供报告使用
        enhanced_plan = self.generate_enhanced_plan_with_combos(recommendations=recommendations, silent=True)
        
        # 生成报告内容 UTC+8时区
        current_time = (datetime.now() + timedelta(hours=8)).strftime('%Y年%m月%d日 %H:%M:%S')
        
        report_content = f"""# 🎯 双色球数据分析报告

## 📊 报告信息
- **生成时间**: {current_time} (UTC+8)
- **数据期数**: 共 {len(self.lottery_data)} 期
- **最新期号**: {self.lottery_data[0]['period'] if self.lottery_data else 'N/A'}
- **数据来源**: 中国福利彩票官方API

## ⚠️ 重要免责声明
**本分析报告仅供学习和研究使用，彩票开奖完全随机。请理性购彩，量力而行！**

---

## 📈 最新开奖信息

"""
        
        # 添加最近5期开奖信息
        if len(self.lottery_data) >= 5:
            report_content += "### 最近5期开奖号码\n\n"
            for i, record in enumerate(self.lottery_data[:5]):
                red_str = " ".join([f"{x:02d}" for x in record['red_balls']])
                report_content += f"**{record['period']}期** ({record['date']}): {red_str} + **{record['blue_ball']:02d}**\n\n"
        
        # 添加号码频率分析
        report_content += """---

## 🔥 号码频率分析

### 红球出现频率排行榜（前15名）

| 排名 | 号码 | 出现次数 | 出现频率 |
|------|------|----------|----------|
"""
        
        red_freq = sorted(red_counter.items(), key=lambda x: x[1], reverse=True)
        for i, (num, count) in enumerate(red_freq[:15], 1):
            percentage = (count / len(self.lottery_data)) * 100
            report_content += f"| {i:02d} | **{num:02d}** | {count} | {percentage:.1f}% |\n"
        
        report_content += """
### 蓝球出现频率排行榜（前10名）

| 排名 | 号码 | 出现次数 | 出现频率 |
|------|------|----------|----------|
"""
        
        blue_freq = sorted(blue_counter.items(), key=lambda x: x[1], reverse=True)
        for i, (num, count) in enumerate(blue_freq[:10], 1):
            percentage = (count / len(self.lottery_data)) * 100
            report_content += f"| {i:02d} | **{num:02d}** | {count} | {percentage:.1f}% |\n"
        
        # 添加规律分析
        report_content += f"""
---

## 📊 号码规律分析

### 奇偶分布统计

{patterns_data['odd_even']}

### 和值分布统计

{patterns_data['sum_dist']}

### 跨度分布统计

{patterns_data['span_dist']}

---

## 📉 走势分析

### 最近10期开奖记录

{trends_data['recent_draws']}

### 热号分析

**最近10期红球热号（出现2次及以上）**: {trends_data['hot_reds']}

**最近10期蓝球热号（出现2次及以上）**: {trends_data['hot_blues']}

---

## 🎯 智能推荐号码

**⚠️ 以下推荐号码仅基于历史统计分析，不保证中奖，请理性参考！**

"""
        
        for i, rec in enumerate(recommendations, 1):
            red_str = " ".join([f"{x:02d}" for x in rec['red_balls']])
            report_content += f"**推荐组合 {i}** ({rec['strategy']}): {red_str} + **{rec['blue_ball']:02d}**\n"
            report_content += f"- 特征: {rec['odd_even']} | 和值:{rec['sum']} | 跨度:{rec['span']}\n"
            report_content += f"- 说明: {rec['description']}\n\n"

        # 如果有增强版复式方案，则补充一节说明
        if enhanced_plan:
            report_content += """---

## 🧩 结构化投注方案（8种策略 + 复式组合）

> 以下组合仍然基于历史统计特征生成，仅用于学习与参考，不保证中奖。

### 8 注 6+1 单式（策略机选）

"""
            singles = enhanced_plan.get("singles_6_1", [])
            for i, t in enumerate(singles, 1):
                red_str = " ".join(f"{x:02d}" for x in t["red_balls"])
                blue_str = " ".join(f"{x:02d}" for x in t["blue_balls"])
                report_content += f"- 单式 {i} ({t['strategy']}): {red_str} + **{blue_str}**\n"

            combo_7_1 = enhanced_plan.get("combo_7_1")
            combo_6_2 = enhanced_plan.get("combo_6_2")

            if combo_7_1:
                red_str = " ".join(f"{x:02d}" for x in combo_7_1["red_balls"])
                blue_str = " ".join(f"{x:02d}" for x in combo_7_1["blue_balls"])
                report_content += f"\n### 7+1 复式组合\n\n- 7+1 ({combo_7_1['source_strategy']}): {red_str} + **{blue_str}**\n"

            if combo_6_2:
                red_str = " ".join(f"{x:02d}" for x in combo_6_2["red_balls"])
                blue_str = " ".join(f"{x:02d}" for x in combo_6_2["blue_balls"])
                report_content += f"\n### 6+2 复式组合\n\n- 6+2 ({combo_6_2['source_strategy']}): {red_str} + **{blue_str}**\n"
        
        # 添加使用说明和提醒
        report_content += f"""---

## 📋 使用说明

### 数据更新频率
- 本报告每天自动更新一次
- 数据来源于中国福利彩票官方API
- 更新时间：每天晚上23:00

### 分析方法说明
1. **频率分析**: 统计每个号码在历史开奖中的出现次数
2. **规律分析**: 分析奇偶分布、和值分布、跨度分布等规律
3. **走势分析**: 观察最近期数的号码走势和热号变化
4. **智能推荐**: 基于统计概率和随机性的权重算法生成推荐号码

### 重要提醒

> 🎲 **彩票本质**: 彩票开奖具有完全的随机性和偶然性
> 
> 🎯 **参考价值**: 本分析仅供统计学习和娱乐参考
> 
> 💰 **理性购彩**: 请根据个人经济能力适度购买
> 
> ⚖️ **法律提醒**: 未满18周岁禁止购买彩票
> 
> 🏠 **家庭和睦**: 切勿因购彩影响家庭生活

---

## 📞 帮助信息

如果您或身边的人出现以下情况，请及时寻求帮助：
- 无法控制购彩行为
- 为了购彩借钱或变卖财产
- 因购彩影响工作、学习或家庭关系
- 出现焦虑、抑郁等心理问题

**全国戒赌帮助热线**: 400-161-9995

---

*报告生成时间: {current_time} (UTC+8)*  
*数据来源: 中国福利彩票官方网站*  
*仅供学习研究使用，请理性购彩*
"""
        
        # 保存报告文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"分析报告已保存到 {filename}")
        except Exception as e:
            print(f"保存分析报告失败: {e}")
    
    def _get_frequency_analysis(self):
        """内部方法：获取频率分析数据"""
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in self.lottery_data:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        return red_counter, blue_counter
    
    def _get_patterns_analysis(self):
        """内部方法：获取规律分析数据"""
        odd_even_dist = defaultdict(int)
        sum_dist = defaultdict(int)
        span_dist = defaultdict(int)
        
        for record in self.lottery_data:
            red_balls = record['red_balls']
            
            # 奇偶分析
            odd_count = sum(1 for x in red_balls if x % 2 == 1)
            even_count = 6 - odd_count
            odd_even_dist[f"{odd_count}奇{even_count}偶"] += 1
            
            # 和值分析
            total_sum = sum(red_balls)
            sum_range = f"{(total_sum//10)*10}-{(total_sum//10)*10+9}"
            sum_dist[sum_range] += 1
            
            # 跨度分析
            span = max(red_balls) - min(red_balls)
            span_range = f"{(span//5)*5}-{(span//5)*5+4}"
            span_dist[span_range] += 1
        
        # 格式化数据
        odd_even_result = "| 分布类型 | 出现次数 | 出现频率 |\n|----------|----------|----------|\n"
        for pattern, count in sorted(odd_even_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.lottery_data)) * 100
            odd_even_result += f"| {pattern} | {count} | {percentage:.1f}% |\n"
        
        sum_result = "| 和值范围 | 出现次数 | 出现频率 |\n|----------|----------|----------|\n"
        for sum_range, count in sorted(sum_dist.items(), key=lambda x: int(x[0].split('-')[0])):
            percentage = (count / len(self.lottery_data)) * 100
            sum_result += f"| {sum_range} | {count} | {percentage:.1f}% |\n"
        
        span_result = "| 跨度范围 | 出现次数 | 出现频率 |\n|----------|----------|----------|\n"
        for span_range, count in sorted(span_dist.items(), key=lambda x: int(x[0].split('-')[0])):
            percentage = (count / len(self.lottery_data)) * 100
            span_result += f"| {span_range} | {count} | {percentage:.1f}% |\n"
        
        return {
            'odd_even': odd_even_result,
            'sum_dist': sum_result,
            'span_dist': span_result
        }
    
    def _get_trends_analysis(self):
        """内部方法：获取趋势分析数据"""
        if len(self.lottery_data) < 10:
            return {
                'recent_draws': '数据不足',
                'hot_reds': '无',
                'hot_blues': '无'
            }
        
        recent_10 = self.lottery_data[:10]
        
        # 格式化最近10期
        recent_draws = "| 期号 | 开奖日期 | 红球号码 | 蓝球 |\n|------|----------|----------|------|\n"
        for record in recent_10:
            red_str = " ".join([f"{x:02d}" for x in record['red_balls']])
            recent_draws += f"| {record['period']} | {record['date']} | {red_str} | **{record['blue_ball']:02d}** |\n"
        
        # 冷热号分析
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in recent_10:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        hot_reds = [num for num, count in red_counter.items() if count >= 2]
        hot_blues = [num for num, count in blue_counter.items() if count >= 2]
        
        hot_reds_str = " ".join([f"{x:02d}" for x in sorted(hot_reds)]) if hot_reds else "无"
        hot_blues_str = " ".join([f"{x:02d}" for x in sorted(hot_blues)]) if hot_blues else "无"
        
        return {
            'recent_draws': recent_draws,
            'hot_reds': hot_reds_str,
            'hot_blues': hot_blues_str
        }
    
    def generate_aggregated_data_hjson(self, filename="data/lottery_aggregated_data.hjson"):
        """生成聚合分析数据的HJSON文件，包含详细注释供AI理解数据用途"""
        print(f"正在生成聚合数据文件: {filename}")
        
        if not self.lottery_data:
            print("无数据，无法生成聚合数据文件")
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # 获取所有分析数据
        red_counter, blue_counter = self._get_frequency_analysis()
        patterns_data = self._get_patterns_analysis_raw()
        trends_data = self._get_trends_analysis_raw()
        recommendations = self.generate_recommendations(num_sets=8)
        
        # 生成时间 UTC+8
        current_time = (datetime.now() + timedelta(hours=8)).strftime('%Y年%m月%d日 %H:%M:%S')
        
        # 构建聚合数据结构
        aggregated_data = {
            "// 数据文件说明": "双色球彩票数据聚合分析结果，包含频率、规律、走势等统计数据",
            "// 文件用途": "供AI系统理解数据含义并生成相应的数据可视化图表",
            "// 更新频率": "每天自动更新一次，与开奖数据同步",
            
            "metadata": {
                "// 元数据说明": "包含数据的基本信息和统计概况",
                "lottery_type": "双色球",
                "lottery_type_en": "double_color_ball", 
                "game_rules": "红球1-33选6个，蓝球1-16选1个",
                "generated_time": current_time,
                "timezone": "UTC+8",
                "total_periods": len(self.lottery_data),
                "latest_period": self.lottery_data[0]['period'] if self.lottery_data else None,
                "latest_date": self.lottery_data[0]['date'] if self.lottery_data else None,
                "data_source": "中国福利彩票官方API"
            },
            
            "frequency_analysis": {
                "// 频率分析说明": "统计每个号码在历史开奖中的出现次数和频率",
                "// 图表建议": "适合绘制柱状图、热力图、频率分布图",
                "// 可视化用途": "展示号码冷热程度，识别高频低频号码",
                
                "red_balls": {
                    "// 红球频率数据": "红球1-33的历史出现统计",
                    "// 数据结构": "number: 号码, count: 出现次数, frequency: 出现频率(%)",
                    "data": [
                        {
                            "number": num,
                            "count": red_counter.get(num, 0),
                            "frequency": round((red_counter.get(num, 0) / len(self.lottery_data)) * 100, 2)
                        } for num in range(1, 34)
                    ],
                    "// 统计摘要": "频率分析的关键指标",
                    "summary": {
                        "highest_freq_number": max(red_counter.items(), key=lambda x: x[1])[0] if red_counter else None,
                        "highest_freq_count": max(red_counter.items(), key=lambda x: x[1])[1] if red_counter else 0,
                        "lowest_freq_number": min(red_counter.items(), key=lambda x: x[1])[0] if red_counter else None,
                        "lowest_freq_count": min(red_counter.items(), key=lambda x: x[1])[1] if red_counter else 0,
                        "average_frequency": round(sum(red_counter.values()) / len(red_counter) if red_counter else 0, 2)
                    }
                },
                
                "blue_balls": {
                    "// 蓝球频率数据": "蓝球1-16的历史出现统计", 
                    "// 数据结构": "number: 号码, count: 出现次数, frequency: 出现频率(%)",
                    "data": [
                        {
                            "number": num,
                            "count": blue_counter.get(num, 0),
                            "frequency": round((blue_counter.get(num, 0) / len(self.lottery_data)) * 100, 2)
                        } for num in range(1, 17)
                    ],
                    "// 统计摘要": "蓝球频率分析的关键指标",
                    "summary": {
                        "highest_freq_number": max(blue_counter.items(), key=lambda x: x[1])[0] if blue_counter else None,
                        "highest_freq_count": max(blue_counter.items(), key=lambda x: x[1])[1] if blue_counter else 0,
                        "lowest_freq_number": min(blue_counter.items(), key=lambda x: x[1])[0] if blue_counter else None,
                        "lowest_freq_count": min(blue_counter.items(), key=lambda x: x[1])[1] if blue_counter else 0,
                        "average_frequency": round(sum(blue_counter.values()) / len(blue_counter) if blue_counter else 0, 2)
                    }
                }
            },
            
            "pattern_analysis": {
                "// 规律分析说明": "分析号码的奇偶分布、和值分布、跨度分布等规律",
                "// 图表建议": "适合绘制饼图、堆叠柱状图、分布直方图",
                "// 可视化用途": "展示号码组合的规律性和分布特征",
                
                "odd_even_distribution": {
                    "// 奇偶分布": "红球6个号码中奇数偶数的分布情况",
                    "// 图表类型": "饼图或柱状图展示各种奇偶组合的出现频率",
                    "data": patterns_data['odd_even_dist'],
                    "total_periods": len(self.lottery_data)
                },
                
                "sum_distribution": {
                    "// 和值分布": "红球6个号码总和的分布区间统计",
                    "// 图表类型": "直方图或折线图展示和值的分布规律",
                    "// 分析意义": "帮助识别号码组合的和值趋势",
                    "data": patterns_data['sum_dist'],
                    "total_periods": len(self.lottery_data)
                },
                
                "span_distribution": {
                    "// 跨度分布": "红球最大号码与最小号码差值的分布统计",
                    "// 图表类型": "柱状图展示不同跨度范围的出现频率",
                    "// 分析意义": "反映号码选择的分散程度",
                    "data": patterns_data['span_dist'],
                    "total_periods": len(self.lottery_data)
                }
            },
            
            "trend_analysis": {
                "// 走势分析说明": "分析最近期数的号码走势和热号变化",
                "// 图表建议": "适合绘制时间序列图、热力图、趋势线图",
                "// 可视化用途": "展示短期内号码的冷热变化趋势",
                "// 分析周期": "最近10期开奖数据",
                
                "recent_draws": trends_data['recent_draws'],
                "hot_numbers": {
                    "// 热号定义": "最近10期中出现2次及以上的号码",
                    "// 图表类型": "标记图或高亮显示热号在走势图中的位置",
                    "red_hot_numbers": trends_data['hot_reds'],
                    "blue_hot_numbers": trends_data['hot_blues']
                }
            },
            
            "recommendations": {
                "// 推荐号码说明": "基于历史统计分析生成的8种策略推荐组合",
                "// 图表建议": "表格展示或卡片式布局展示推荐组合",
                "// 重要提醒": "仅供参考，彩票开奖完全随机",
                "// 策略说明": "包含高频主导、均衡分布、冷热结合等多种选号策略",
                
                "strategies": [
                    {
                        "strategy_name": rec['strategy'],
                        "description": rec['description'],
                        "red_balls": rec['red_balls'],
                        "blue_ball": rec['blue_ball'],
                        "characteristics": {
                            "odd_even_ratio": rec['odd_even'],
                            "sum_value": rec['sum'],
                            "span_value": rec['span']
                        }
                    } for rec in recommendations
                ],
                
                "strategy_summary": {
                    "total_strategies": len(recommendations),
                    "strategy_types": [rec['strategy'] for rec in recommendations]
                }
            },
            
            "visualization_suggestions": {
                "// 可视化建议": "针对不同数据类型的图表绘制建议",
                
                "frequency_charts": {
                    "chart_types": ["bar_chart", "heatmap", "bubble_chart"],
                    "description": "频率数据适合用柱状图展示排名，热力图展示分布，气泡图展示频率大小"
                },
                
                "pattern_charts": {
                    "chart_types": ["pie_chart", "stacked_bar", "histogram"],
                    "description": "规律数据适合用饼图展示比例，堆叠柱状图展示分类，直方图展示分布"
                },
                
                "trend_charts": {
                    "chart_types": ["line_chart", "scatter_plot", "timeline"],
                    "description": "走势数据适合用折线图展示变化，散点图展示分布，时间轴展示历史"
                },
                
                "recommendation_display": {
                    "display_types": ["table", "card_layout", "grid_view"],
                    "description": "推荐数据适合用表格展示详情，卡片布局展示策略，网格视图展示组合"
                }
            }
        }
        
        # 保存HJSON文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                hjson.dump(aggregated_data, f, ensure_ascii=False, indent=2)
            print(f"聚合数据文件已保存到 {filename}")
        except Exception as e:
            print(f"保存聚合数据文件失败: {e}")
    
    def _get_patterns_analysis_raw(self):
        """内部方法：获取原始规律分析数据"""
        odd_even_dist = defaultdict(int)
        sum_dist = defaultdict(int)
        span_dist = defaultdict(int)
        
        for record in self.lottery_data:
            red_balls = record['red_balls']
            
            # 奇偶分析
            odd_count = sum(1 for x in red_balls if x % 2 == 1)
            even_count = 6 - odd_count
            odd_even_dist[f"{odd_count}奇{even_count}偶"] += 1
            
            # 和值分析
            total_sum = sum(red_balls)
            sum_range = f"{(total_sum//10)*10}-{(total_sum//10)*10+9}"
            sum_dist[sum_range] += 1
            
            # 跨度分析
            span = max(red_balls) - min(red_balls)
            span_range = f"{(span//5)*5}-{(span//5)*5+4}"
            span_dist[span_range] += 1
        
        return {
            'odd_even_dist': dict(odd_even_dist),
            'sum_dist': dict(sum_dist),
            'span_dist': dict(span_dist)
        }
    
    def _get_trends_analysis_raw(self):
        """内部方法：获取原始趋势分析数据"""
        if len(self.lottery_data) < 10:
            return {
                'recent_draws': [],
                'hot_reds': [],
                'hot_blues': []
            }
        
        recent_10 = self.lottery_data[:10]
        
        # 最近10期数据
        recent_draws = []
        for record in recent_10:
            recent_draws.append({
                'period': record['period'],
                'date': record['date'],
                'red_balls': record['red_balls'],
                'blue_ball': record['blue_ball']
            })
        
        # 冷热号分析
        red_counter = Counter()
        blue_counter = Counter()
        
        for record in recent_10:
            for red in record['red_balls']:
                red_counter[red] += 1
            blue_counter[record['blue_ball']] += 1
        
        hot_reds = [num for num, count in red_counter.items() if count >= 2]
        hot_blues = [num for num, count in blue_counter.items() if count >= 2]
        
        return {
            'recent_draws': recent_draws,
            'hot_reds': sorted(hot_reds),
            'hot_blues': sorted(hot_blues)
        }
    
    def update_readme_recommendations(self, readme_path="README.md", timestamp=None):
        """更新README.md中的推荐号码"""
        print(f"正在更新README.md中的双色球推荐号码...")
        
        if not self.lottery_data:
            print("无数据，无法更新README推荐号码")
            return
        
        try:
            # 生成推荐号码
            recommendations = self.generate_recommendations(num_sets=5)
            
            # 读取现有README内容
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用传入的时间戳或生成新的时间戳 UTC+8
            if timestamp:
                current_time = timestamp
            else:
                current_time = (datetime.now() + timedelta(hours=8)).strftime('%Y年%m月%d日 %H:%M:%S')
            
            # 构建推荐号码内容
            recommendations_content = f"""## 🎯 今日推荐号码

**⚠️ 以下推荐号码基于历史统计分析，仅供参考！**

### 双色球推荐 (更新时间: {current_time})

"""
            
            for i, rec in enumerate(recommendations, 1):
                red_str = " ".join([f"{x:02d}" for x in rec['red_balls']])
                recommendations_content += f"**推荐 {i}** ({rec['strategy']}): `{red_str}` + `{rec['blue_ball']:02d}`  \n"
                recommendations_content += f"*{rec['description']} | {rec['odd_even']} | 和值:{rec['sum']} | 跨度:{rec['span']}*\n\n"
            
            # 查找第二个H2标题的位置（免责声明后）
            lines = content.split('\n')
            h2_count = 0
            insert_index = -1
            
            for i, line in enumerate(lines):
                if line.startswith('## '):
                    h2_count += 1
                    if h2_count == 2:  # 第二个H2标题
                        insert_index = i
                        break
            
            if insert_index == -1:
                print("未找到合适的插入位置，将在文件末尾添加")
                new_content = content + "\n\n" + recommendations_content
            else:
                # 检查是否已存在推荐号码部分
                existing_rec_index = -1
                for i in range(insert_index, len(lines)):
                    if "今日推荐号码" in lines[i]:
                        existing_rec_index = i
                        break
                
                if existing_rec_index != -1:
                    # 找到推荐号码部分的结束位置
                    end_index = existing_rec_index
                    for i in range(existing_rec_index + 1, len(lines)):
                        if lines[i].startswith('## '):
                            end_index = i
                            break
                    else:
                        end_index = len(lines)
                    
                    # 替换现有推荐号码部分
                    new_lines = lines[:existing_rec_index] + recommendations_content.strip().split('\n') + lines[end_index:]
                else:
                    # 在第二个H2标题前插入推荐号码
                    new_lines = lines[:insert_index] + recommendations_content.strip().split('\n') + [''] + lines[insert_index:]
                
                new_content = '\n'.join(new_lines)
            
            # 写回文件
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"README.md中的双色球推荐号码已更新")
            
        except Exception as e:
            print(f"更新README推荐号码失败: {e}")

def main():
    """主函数"""
    # 显示免责声明
    print("=" * 80)
    print("🎯 双色球数据分析系统")
    print("=" * 80)
    print("⚠️  重要免责声明：")
    print("• 彩票开奖完全随机")
    print("• 本分析仅供学习参考，不构成投注建议")
    print("• 请理性购彩，量力而行，未满18周岁禁止购买")
    print("• 使用本软件产生的任何后果由用户自行承担")
    print("=" * 80)
    
    analyzer = DoubleColorBallAnalyzer()
    
    print("\n双色球开奖数据分析系统")
    print("=" * 50)
    
    # 始终抓取最新数据，覆盖现有文件
    print("⚠️  正在抓取最新数据，请确保网络连接正常...")
    max_pages = analyzer.get_max_pages()
    analyzer.fetch_lottery_data(max_pages=max_pages)
    analyzer.save_data()
    
    if not analyzer.lottery_data:
        print("❌ 无法获取数据，程序退出")
        return
    
    # 显示游戏规则
    analyzer.get_lottery_rules()
    
    # 执行各种分析
    red_counter, blue_counter = analyzer.analyze_frequency()
    analyzer.analyze_patterns()
    analyzer.analyze_trends()
    
    # 生成推荐号码
    recommendations = analyzer.generate_recommendations(num_sets=5)
    
    # 生成可视化图表
    try:
        analyzer.visualize_frequency()
    except Exception as e:
        print(f"⚠️  图表生成失败: {e}")
        print("可能是字体问题，请检查系统中文字体支持")
    
    # 生成分析报告
    analyzer.generate_analysis_report()
    
    # 生成聚合数据文件
    analyzer.generate_aggregated_data_hjson()
    
    # 更新README.md中的推荐号码
    analyzer.update_readme_recommendations()
    
    print("\n" + "=" * 50)
    print("📋 重要提醒：")
    print("• 以上推荐号码基于历史统计，仅供参考")
    print("• 彩票具有偶然性，请勿过度依赖任何预测")
    print("• 理性购彩，适度娱乐，珍惜家庭和睦")
    print("• 如有赌博问题，请寻求专业帮助")
    print("=" * 50)
    print("✅ 分析完成！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        print("请检查网络连接和依赖库安装情况") 