"""
Seed initial data into the database.
Run: python seed.py
"""
from database import SessionLocal
from models.staff import Staff
from models.service import Service, ServiceCategory
from models.customer import Customer
from models.user import User
from models.inventory import InventoryItem
from models.product import Product
from auth import hash_password


def seed():
    db = SessionLocal()

    # Categories
    categories = ['美髮']
    cat_objs = {}
    for name in categories:
        c = ServiceCategory(name=name)
        db.add(c)
        db.flush()
        cat_objs[name] = c.id

    # Staff
    staff_data = [
        dict(name='Vicky', color='#f56a00', phone='0912-111-111', skills=['剪髮', '造型'], commission_rate=35),
        dict(name='Kevin', color='#7265e6', phone='0912-222-222', skills=['染髮', '燙髮'], commission_rate=40),
        dict(name='Mina', color='#00a2ae', phone='0912-333-333', skills=['護髮', '頭皮保養'], commission_rate=35),
        dict(name='Allen', color='#e6704a', phone='0912-444-444', skills=['剪髮', '燙髮', '染髮'], commission_rate=38),
    ]
    staff_objs = []
    for s in staff_data:
        obj = Staff(**s)
        db.add(obj)
        db.flush()
        staff_objs.append(obj)

    # Services
    service_data = [
        dict(name='設計剪髮', category_id=cat_objs['美髮'], duration=60, price=800),
        dict(name='男士剪髮', category_id=cat_objs['美髮'], duration=45, price=600),
        dict(name='髮根補染', category_id=cat_objs['美髮'], duration=90, price=1800),
        dict(name='快速染髮', category_id=cat_objs['美髮'], duration=120, price=2600),
        dict(name='質感染髮', category_id=cat_objs['美髮'], duration=150, price=3200),
        dict(name='手刷染（Balayage）', category_id=cat_objs['美髮'], duration=180, price=4200),
        dict(name='挑染/耳圈染', category_id=cat_objs['美髮'], duration=120, price=2800),
        dict(name='冷燙', category_id=cat_objs['美髮'], duration=150, price=3000),
        dict(name='溫塑燙髮', category_id=cat_objs['美髮'], duration=180, price=3600),
        dict(name='韓式髮根燙', category_id=cat_objs['美髮'], duration=90, price=2000),
        dict(name='縮毛矯正', category_id=cat_objs['美髮'], duration=210, price=4200),
        dict(name='深層護髮', category_id=cat_objs['美髮'], duration=40, price=1200),
        dict(name='角蛋白護髮', category_id=cat_objs['美髮'], duration=90, price=2600),
        dict(name='水光護髮', category_id=cat_objs['美髮'], duration=75, price=2200),
        dict(name='頭皮去角質', category_id=cat_objs['美髮'], duration=40, price=1000),
        dict(name='頭皮淨化護理', category_id=cat_objs['美髮'], duration=50, price=1500),
    ]
    # Products（美髮）
    product_data = [
        dict(name='角蛋白洗髮精', category='洗護', price=680, cost=220, stock=32, barcode='HAIR001'),
        dict(name='修護潤髮乳', category='洗護', price=720, cost=250, stock=26, barcode='HAIR002'),
        dict(name='染後鎖色髮膜', category='染後護理', price=980, cost=360, stock=18, barcode='HAIR003'),
        dict(name='頭皮淨化精華', category='頭皮護理', price=1280, cost=480, stock=14, barcode='HAIR004'),
        dict(name='霧感造型噴霧', category='造型', price=560, cost=180, stock=22, barcode='HAIR005'),
        dict(name='抗熱修護噴霧', category='造型', price=620, cost=210, stock=20, barcode='HAIR006'),
        dict(name='免沖洗護髮油', category='染後護理', price=760, cost=260, stock=24, barcode='HAIR007'),
    ]
    for p in product_data:
        db.add(Product(**p))

    for s in service_data:
        db.add(Service(**s))

    # Customers
    customer_data = [
        dict(name='陳小姐', phone='0912-345-678', email='chen@example.com', level='VIP', points=3200, balance=5000, total_spent=28000, visits=14),
        dict(name='林太太', phone='0923-456-789', level='一般', points=800, balance=0, total_spent=6500, visits=5),
        dict(name='王小姐', phone='0934-567-890', level='黃金', points=1500, balance=2000, total_spent=15000, visits=9),
        dict(name='張女士', phone='0945-678-901', level='VIP', points=5600, balance=8000, total_spent=52000, visits=26),
    ]
    for c in customer_data:
        db.add(Customer(**c))

    # Users
    db.add(User(name='系統管理員', email='admin@beauty-pos.com',
                hashed_password=hash_password('admin1234'), role='admin'))
    for i, s in enumerate(staff_objs):
        db.add(User(
            name=s.name, email=f'staff{i+1}@beauty-pos.com',
            hashed_password=hash_password('staff1234'), role='staff',
            staff_id=s.id,
        ))

    # Inventory
    inventory_data = [
        dict(name='燙髮藥水 A 劑', category='美髮', unit='ml', quantity=2000, low_stock_threshold=500, cost_per_unit=0.2),
        dict(name='燙髮藥水 B 劑', category='美髮', unit='ml', quantity=1800, low_stock_threshold=500, cost_per_unit=0.2),
        dict(name='染膏（自然棕）', category='美髮', unit='條', quantity=45, low_stock_threshold=10, cost_per_unit=120),
        dict(name='雙氧乳 6%', category='美髮', unit='ml', quantity=5000, low_stock_threshold=1200, cost_per_unit=0.05),
        dict(name='雙氧乳 9%', category='美髮', unit='ml', quantity=3200, low_stock_threshold=800, cost_per_unit=0.06),
        dict(name='護髮精華', category='美髮', unit='ml', quantity=2400, low_stock_threshold=600, cost_per_unit=0.18),
        dict(name='造型噴霧補充液', category='美髮', unit='ml', quantity=1500, low_stock_threshold=400, cost_per_unit=0.12),
        dict(name='頭皮淨化液', category='美髮', unit='ml', quantity=1800, low_stock_threshold=500, cost_per_unit=0.16),
        dict(name='護髮蒸氣帽', category='美髮', unit='個', quantity=18, low_stock_threshold=5, cost_per_unit=180),
        dict(name='染髮隔離耳套', category='美髮', unit='組', quantity=120, low_stock_threshold=30, cost_per_unit=6),
    ]
    for item in inventory_data:
        db.add(InventoryItem(**item))

    db.commit()
    db.close()
    print("Seed complete.")
    print("Admin login: admin@beauty-pos.com / admin1234")
    print("Staff login: staff1@beauty-pos.com / staff1234")


if __name__ == '__main__':
    seed()
