#!/usr/bin/env python3
import os
import re
import json
import argparse
from collections import defaultdict
from typing import List, Dict, Any
import datetime

class LogParser:
    def __init__(self):
        self.log_pattern = re.compile(
            r'(?P<ip>\S+) - - \[(?P<time>.*?)\] "(?P<request>.*?)" '
            r'(?P<status>\d+) (?P<bytes>\d+) "(?P<referer>.*?)" '
            r'"(?P<user_agent>.*?)" (?P<duration>\d+)'
        )
        
    def parse_line(self, line: str) -> Dict[str, Any]:
        match = self.log_pattern.match(line)
        if not match:
            return None
            
        data = match.groupdict()
        
        # Парсим метод и URL из request
        request_parts = data['request'].split()
        if len(request_parts) >= 2:
            data['method'] = request_parts[0]
            data['url'] = request_parts[1]
        else:
            data['method'] = 'UNKNOWN'
            data['url'] = ''
            
        # Конвертируем типы данных
        data['status'] = int(data['status'])
        data['bytes'] = int(data['bytes'])
        data['duration'] = int(data['duration'])
        
        # Парсим время
        try:
            # Формат: 23/Dec/2015:07:27:57 +0100
            time_str = data['time'].split()[0]
            data['timestamp'] = datetime.datetime.strptime(
                time_str, '%d/%b/%Y:%H:%M:%S'
            )
        except:
            data['timestamp'] = None
            
        return data

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        stats = {
            'total_requests': 0,
            'methods': defaultdict(int),
            'ip_requests': defaultdict(int),
            'longest_requests': [],
            'file_name': os.path.basename(file_path)
        }
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed = self.parse_line(line.strip())
                if not parsed:
                    continue
                    
                stats['total_requests'] += 1
                stats['methods'][parsed['method']] += 1
                stats['ip_requests'][parsed['ip']] += 1
                
                # Обновляем топ самых долгих запросов
                request_info = {
                    'method': parsed['method'],
                    'url': parsed['url'],
                    'ip': parsed['ip'],
                    'duration': parsed['duration'],
                    'time': parsed['time'],
                    'timestamp': parsed['timestamp'].isoformat() if parsed['timestamp'] else None
                }
                
                stats['longest_requests'].append(request_info)
                # Сортируем и оставляем только топ 3
                stats['longest_requests'].sort(key=lambda x: x['duration'], reverse=True)
                stats['longest_requests'] = stats['longest_requests'][:3]
        
        # Получаем топ 3 IP
        top_ips = sorted(
            stats['ip_requests'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        stats['top_ips'] = [{'ip': ip, 'count': count} for ip, count in top_ips]
        
        # Убираем временные данные
        del stats['ip_requests']
        
        return stats

    def process_path(self, path: str) -> List[Dict[str, Any]]:
        results = []
        
        if os.path.isfile(path):
            results.append(self.analyze_file(path))
        elif os.path.isdir(path):
            for filename in os.listdir(path):
                if filename.endswith('.log'):
                    file_path = os.path.join(path, filename)
                    results.append(self.analyze_file(file_path))
        
        return results

    def print_stats(self, stats: Dict[str, Any]):
        print(f"\n=== Статистика для файла: {stats['file_name']} ===")
        print(f"Общее количество запросов: {stats['total_requests']}")
        print("\nКоличество запросов по методам:")
        for method, count in stats['methods'].items():
            print(f"  {method}: {count}")
        
        print("\nТоп 3 IP адресов:")
        for i, ip_info in enumerate(stats['top_ips'], 1):
            print(f"  {i}. {ip_info['ip']} - {ip_info['count']} запросов")
        
        print("\nТоп 3 самых долгих запросов:")
        for i, req in enumerate(stats['longest_requests'], 1):
            print(f"  {i}. {req['method']} {req['url']}")
            print(f"     IP: {req['ip']}, Длительность: {req['duration']}ms")
            print(f"     Время: {req['time']}")

def main():
    parser = argparse.ArgumentParser(description='Анализатор access.log файлов')
    parser.add_argument('path', help='Путь к файлу или директории с логами')
    parser.add_argument('--output', '-o', help='Директория для сохранения JSON результатов')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Ошибка: путь '{args.path}' не существует")
        return
    
    log_parser = LogParser()
    results = log_parser.process_path(args.path)
    
    if not results:
        print("Не найдено подходящих .log файлов")
        return
    
    # Сохраняем результаты
    output_dir = args.output or '.'
    os.makedirs(output_dir, exist_ok=True)
    
    for stats in results:
        # Вывод в терминал
        log_parser.print_stats(stats)
        
        # Сохранение в JSON
        output_file = os.path.join(
            output_dir, 
            f"stats_{stats['file_name']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"\nРезультаты сохранены в: {output_file}")

if __name__ == '__main__':
    main()