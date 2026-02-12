#!/usr/bin/env python3
"""
测试数据生成器
生成测试用的 JSON、CSV、YAML 数据文件
"""

import json
import csv
import yaml
import sys
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path


def generate_user_data(num_users: int = 10) -> List[Dict[str, Any]]:
    """生成用户测试数据"""
    users = []

    first_names = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
    last_names = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军"]
    domains = ["example.com", "test.com", "demo.com", "sample.com"]

    for i in range(1, num_users + 1):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        username = f"user{i:03d}"
        email = f"{username}@{random.choice(domains)}"

        user = {
            "id": i,
            "username": username,
            "email": email,
            "password": f"Test@123456{i}",
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name}{last_name}",
            "age": random.randint(18, 65),
            "gender": random.choice(["male", "female"]),
            "phone": f"138{random.randint(1000, 9999):04d}{random.randint(1000, 9999):04d}",
            "address": f"测试地址{i}号",
            "city": random.choice(["北京", "上海", "广州", "深圳", "杭州", "成都"]),
            "country": "中国",
            "zip_code": f"{random.randint(100000, 999999)}",
            "registration_date": (
                datetime.now() - timedelta(days=random.randint(1, 365))
            ).strftime("%Y-%m-%d"),
            "last_login": (
                datetime.now() - timedelta(days=random.randint(0, 30))
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "status": random.choice(["active", "inactive", "suspended"]),
            "role": random.choice(
                ["user", "user", "user", "admin"]
            ),  # 大部分是普通用户
            "preferences": {
                "theme": random.choice(["light", "dark"]),
                "language": random.choice(["zh-CN", "en-US"]),
                "notifications": random.choice([True, False]),
            },
        }
        users.append(user)

    return users


def generate_product_data(num_products: int = 20) -> List[Dict[str, Any]]:
    """生成产品测试数据"""
    products = []

    categories = ["电子产品", "服装", "食品", "家居", "图书", "美妆", "运动", "玩具"]
    brands = {
        "电子产品": ["苹果", "华为", "小米", "三星", "联想"],
        "服装": ["优衣库", "ZARA", "H&M", "耐克", "阿迪达斯"],
        "食品": ["可口可乐", "百事", "雀巢", "蒙牛", "伊利"],
        "家居": ["宜家", "MUJI", "海尔", "美的", "格力"],
        "图书": ["商务印书馆", "人民文学", "中华书局", "清华大学出版社", "机械工业"],
        "美妆": ["兰蔻", "雅诗兰黛", "香奈儿", "迪奥", "欧莱雅"],
        "运动": ["耐克", "阿迪达斯", "安踏", "李宁", "彪马"],
        "玩具": ["乐高", "孩之宝", "美泰", "万代", "迪士尼"],
    }

    for i in range(1, num_products + 1):
        category = random.choice(categories)
        brand = random.choice(brands.get(category, ["测试品牌"]))

        product = {
            "id": i,
            "sku": f"SKU{random.randint(10000, 99999):05d}",
            "name": f"测试产品{i}",
            "description": f"这是第{i}个测试产品的描述，属于{category}类别，品牌是{brand}。",
            "category": category,
            "subcategory": f"{category}子类",
            "brand": brand,
            "price": round(random.uniform(10.0, 1000.0), 2),
            "original_price": round(random.uniform(15.0, 1200.0), 2),
            "currency": "CNY",
            "stock_quantity": random.randint(0, 1000),
            "weight": round(random.uniform(0.1, 10.0), 2),
            "dimensions": {
                "length": round(random.uniform(5.0, 50.0), 1),
                "width": round(random.uniform(5.0, 50.0), 1),
                "height": round(random.uniform(5.0, 50.0), 1),
                "unit": "cm",
            },
            "rating": round(random.uniform(3.0, 5.0), 1),
            "review_count": random.randint(0, 1000),
            "tags": [category, brand, "测试", f"标签{i % 5}"],
            "images": [
                f"https://example.com/images/product{i}_1.jpg",
                f"https://example.com/images/product{i}_2.jpg",
            ],
            "features": [f"功能{i}.1", f"功能{i}.2", f"功能{i}.3"],
            "specifications": {
                "material": random.choice(["塑料", "金属", "布料", "木材", "玻璃"]),
                "color": random.choice(
                    ["红色", "蓝色", "绿色", "黑色", "白色", "银色"]
                ),
                "size": random.choice(["S", "M", "L", "XL", "XXL"]),
                "warranty": f"{random.randint(1, 3)}年",
            },
            "created_at": (
                datetime.now() - timedelta(days=random.randint(1, 365))
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (
                datetime.now() - timedelta(days=random.randint(0, 30))
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "is_active": random.choice([True, True, True, False]),  # 大部分是激活状态
            "is_featured": random.choice([True, False]),
            "is_on_sale": random.choice([True, False]),
        }
        products.append(product)

    return products


def generate_order_data(
    num_orders: int = 15,
    users: Optional[List[Dict]] = None,
    products: Optional[List[Dict]] = None,
) -> List[Dict[str, Any]]:
    """生成订单测试数据"""
    orders = []

    if not users:
        users = generate_user_data(5)
    if not products:
        products = generate_product_data(10)

    statuses = [
        "pending",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
        "refunded",
    ]
    payment_methods = [
        "credit_card",
        "debit_card",
        "paypal",
        "alipay",
        "wechat_pay",
        "bank_transfer",
    ]
    shipping_methods = ["standard", "express", "next_day", "pickup"]

    for i in range(1, num_orders + 1):
        user = random.choice(users)
        num_items = random.randint(1, 5)
        order_items = []

        subtotal = 0
        for j in range(num_items):
            product = random.choice(products)
            quantity = random.randint(1, 3)
            price = product["price"]
            item_total = price * quantity

            order_item = {
                "product_id": product["id"],
                "product_name": product["name"],
                "sku": product["sku"],
                "quantity": quantity,
                "unit_price": price,
                "total_price": item_total,
                "image_url": product["images"][0] if product["images"] else "",
            }
            order_items.append(order_item)
            subtotal += item_total

        shipping_cost = round(random.uniform(0.0, 50.0), 2)
        tax = round(subtotal * random.uniform(0.05, 0.15), 2)
        total = subtotal + shipping_cost + tax

        order_date = datetime.now() - timedelta(days=random.randint(0, 90))

        order = {
            "id": i,
            "order_number": f"ORD{random.randint(100000, 999999):06d}",
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "order_date": order_date.strftime("%Y-%m-%d %H:%M:%S"),
            "status": random.choice(statuses),
            "payment_method": random.choice(payment_methods),
            "payment_status": random.choice(["paid", "pending", "failed"]),
            "shipping_method": random.choice(shipping_methods),
            "shipping_address": {
                "recipient": user["full_name"],
                "phone": user["phone"],
                "address": user["address"],
                "city": user["city"],
                "country": user["country"],
                "zip_code": user["zip_code"],
            },
            "billing_address": {
                "recipient": user["full_name"],
                "phone": user["phone"],
                "address": user["address"],
                "city": user["city"],
                "country": user["country"],
                "zip_code": user["zip_code"],
            },
            "items": order_items,
            "subtotal": round(subtotal, 2),
            "shipping_cost": shipping_cost,
            "tax": tax,
            "total": round(total, 2),
            "currency": "CNY",
            "notes": f"测试订单{i}的备注信息",
            "tracking_number": f"TRK{random.randint(1000000000, 9999999999)}"
            if random.choice([True, False])
            else None,
            "estimated_delivery": (
                order_date + timedelta(days=random.randint(1, 7))
            ).strftime("%Y-%m-%d"),
            "actual_delivery": (
                order_date + timedelta(days=random.randint(1, 10))
            ).strftime("%Y-%m-%d")
            if random.choice([True, False])
            else None,
            "cancellation_reason": random.choice(
                ["", "客户取消", "库存不足", "地址错误"]
            )
            if random.choice([True, False])
            else "",
        }
        orders.append(order)

    return orders


def generate_api_test_data() -> Dict[str, Any]:
    """生成 API 测试数据"""
    return {
        "valid_requests": {
            "create_user": {
                "username": "testuser",
                "email": "test@example.com",
                "password": "Test@123456",
                "first_name": "张",
                "last_name": "三",
                "age": 25,
                "gender": "male",
            },
            "update_user": {
                "first_name": "李",
                "last_name": "四",
                "age": 30,
                "email": "updated@example.com",
            },
            "login": {"username": "testuser", "password": "Test@123456"},
            "create_product": {
                "name": "测试产品",
                "description": "这是一个测试产品",
                "price": 99.99,
                "category": "电子产品",
                "stock_quantity": 100,
            },
            "place_order": {
                "user_id": 1,
                "items": [
                    {"product_id": 1, "quantity": 2},
                    {"product_id": 2, "quantity": 1},
                ],
                "shipping_address": {
                    "recipient": "张三",
                    "address": "测试地址123号",
                    "city": "北京",
                    "country": "中国",
                    "zip_code": "100000",
                },
            },
        },
        "invalid_requests": {
            "empty_fields": {"username": "", "email": "", "password": ""},
            "invalid_email": {
                "username": "testuser",
                "email": "invalid-email",
                "password": "Test@123456",
            },
            "short_password": {
                "username": "testuser",
                "email": "test@example.com",
                "password": "123",
            },
            "negative_price": {
                "name": "测试产品",
                "price": -10.0,
                "category": "电子产品",
            },
            "missing_required": {
                "name": "测试产品"
                # 缺少必填字段 price, category
            },
        },
        "edge_cases": {
            "max_length_fields": {
                "username": "a" * 50,
                "email": f"{'a' * 50}@example.com",
                "description": "测试描述" * 100,
            },
            "special_characters": {
                "username": "test_user-123.456",
                "email": "test.user+tag@example.com",
                "name": "产品名称@#$%^&*()",
            },
            "unicode_characters": {
                "username": "测试用户",
                "email": "测试@例子.com",
                "description": "中文描述测试 🚀✨✅",
            },
            "boundary_values": {"age": 0, "price": 0.01, "quantity": 1, "rating": 5.0},
        },
    }


def save_json(data: Any, filepath: str):
    """保存为 JSON 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"保存 JSON 文件: {filepath}")


def save_csv(data: List[Dict[str, Any]], filepath: str):
    """保存为 CSV 文件"""
    if not data:
        print(f"警告: 无数据可保存到 {filepath}")
        return

    # 提取所有可能的键
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_keys))
        writer.writeheader()

        for item in data:
            # 展平嵌套字典
            flat_item = {}
            for key, value in item.items():
                if isinstance(value, dict):
                    # 将嵌套字典转换为 JSON 字符串
                    flat_item[key] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, list):
                    # 将列表转换为 JSON 字符串
                    flat_item[key] = json.dumps(value, ensure_ascii=False)
                else:
                    flat_item[key] = value
            writer.writerow(flat_item)

    print(f"保存 CSV 文件: {filepath}")


def save_yaml(data: Any, filepath: str):
    """保存为 YAML 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    print(f"保存 YAML 文件: {filepath}")


def generate_all_test_data(output_dir: str = "test_data"):
    """生成所有测试数据"""
    os.makedirs(output_dir, exist_ok=True)

    print("生成测试数据...")

    # 生成用户数据
    users = generate_user_data(20)
    save_json(users, os.path.join(output_dir, "users.json"))
    save_csv(users, os.path.join(output_dir, "users.csv"))

    # 生成产品数据
    products = generate_product_data(30)
    save_json(products, os.path.join(output_dir, "products.json"))
    save_csv(products, os.path.join(output_dir, "products.csv"))

    # 生成订单数据
    orders = generate_order_data(25, users, products)
    save_json(orders, os.path.join(output_dir, "orders.json"))
    save_csv(orders, os.path.join(output_dir, "orders.csv"))

    # 生成 API 测试数据
    api_data = generate_api_test_data()
    save_json(api_data, os.path.join(output_dir, "api_test_data.json"))
    save_yaml(api_data, os.path.join(output_dir, "api_test_data.yaml"))

    # 生成测试配置
    test_config = {
        "test_environment": {
            "name": "测试环境",
            "api_base_url": "http://localhost:8080",
            "ui_base_url": "http://localhost:3000",
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "test_db",
                "username": "test_user",
                "password": "test_password",
            },
        },
        "test_users": {
            "admin": {"username": "admin", "password": "Admin@123456", "role": "admin"},
            "regular_user": {
                "username": "user1",
                "password": "User@123456",
                "role": "user",
            },
            "inactive_user": {
                "username": "inactive_user",
                "password": "Inactive@123456",
                "role": "user",
                "status": "inactive",
            },
        },
        "test_products": {
            "featured_product": {"id": 1, "name": "特色测试产品", "price": 199.99},
            "out_of_stock_product": {
                "id": 2,
                "name": "缺货测试产品",
                "price": 99.99,
                "stock_quantity": 0,
            },
            "on_sale_product": {
                "id": 3,
                "name": "促销测试产品",
                "price": 49.99,
                "original_price": 99.99,
            },
        },
    }

    save_json(test_config, os.path.join(output_dir, "test_config.json"))
    save_yaml(test_config, os.path.join(output_dir, "test_config.yaml"))

    # 生成数据统计
    stats = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_summary": {
            "users": len(users),
            "products": len(products),
            "orders": len(orders),
            "api_test_cases": len(api_data.get("valid_requests", {}))
            + len(api_data.get("invalid_requests", {}))
            + len(api_data.get("edge_cases", {})),
        },
        "file_summary": {
            "json_files": [
                "users.json",
                "products.json",
                "orders.json",
                "api_test_data.json",
                "test_config.json",
            ],
            "csv_files": ["users.csv", "products.csv", "orders.csv"],
            "yaml_files": ["api_test_data.yaml", "test_config.yaml"],
        },
    }

    save_json(stats, os.path.join(output_dir, "data_stats.json"))

    print()
    print("测试数据生成完成!")
    print(f"输出目录: {output_dir}")
    print(f"生成 {len(users)} 个用户")
    print(f"生成 {len(products)} 个产品")
    print(f"生成 {len(orders)} 个订单")
    print(f"生成 {stats['data_summary']['api_test_cases']} 个 API 测试用例")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="生成测试数据")
    parser.add_argument(
        "--output", "-o", default="test_data", help="输出目录 (默认: test_data)"
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "users", "products", "orders", "api"],
        default="all",
        help="数据类型 (默认: all)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv", "yaml", "all"],
        default="all",
        help="输出格式 (默认: all)",
    )
    parser.add_argument(
        "--count", "-c", type=int, default=10, help="数据数量 (默认: 10)"
    )

    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    if args.type == "all":
        generate_all_test_data(output_dir)
    else:
        if args.type == "users":
            data = generate_user_data(args.count)
            filename = "users"
        elif args.type == "products":
            data = generate_product_data(args.count)
            filename = "products"
        elif args.type == "orders":
            data = generate_order_data(args.count)
            filename = "orders"
        elif args.type == "api":
            data = generate_api_test_data()
            filename = "api_test_data"
        else:
            # 不应该发生，因为args.type有choices限制
            print(f"错误: 未知的数据类型: {args.type}")
            sys.exit(1)

        base_path = os.path.join(output_dir, filename)

        if args.format in ["json", "all"]:
            save_json(data, f"{base_path}.json")
        if args.format in ["csv", "all"] and isinstance(data, list):
            save_csv(data, f"{base_path}.csv")
        if args.format in ["yaml", "all"]:
            save_yaml(data, f"{base_path}.yaml")


if __name__ == "__main__":
    main()
