from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from database import get_db
from models.booking import Booking, BookingItem, BookingStatus
from models.customer import Customer
from models.service import Service
from models.product import Product
from models.payment import Payment
from models.coupon import Coupon, CouponUsage
from models.commission import Commission
from models.staff import Staff
from ws_manager import manager
import asyncio
from auth import require_auth
from api_errors import api_error
from audit import audit_event

router = APIRouter(prefix="/checkout", tags=["checkout"])


class CheckoutItem(BaseModel):
    type: str = "service"          # service | product
    item_id: int
    staff_id: int
    price: Decimal
    is_designated: bool = False


class PaymentEntry(BaseModel):
    method: str
    amount: Decimal


class CheckoutRequest(BaseModel):
    customer_id: Optional[int] = None
    coupon_code: Optional[str] = None
    payments: List[PaymentEntry]
    items: List[CheckoutItem]


class CheckoutResponse(BaseModel):
    booking_id: int
    subtotal: Decimal
    coupon_discount: Decimal
    total: Decimal
    points_earned: int
    payments: List[PaymentEntry]


@router.post("/", response_model=CheckoutResponse)
async def checkout(payload: CheckoutRequest, db: Session = Depends(get_db), user=Depends(require_auth)):
    if not payload.items:
        raise api_error(400, "EMPTY_CHECKOUT", "No items")

    subtotal = sum(i.price for i in payload.items)

    # 驗證優惠券
    coupon_discount = Decimal("0")
    coupon_obj = None
    if payload.coupon_code:
        coupon_obj = db.query(Coupon).filter(
            Coupon.code == payload.coupon_code.upper(),
            Coupon.is_active == 1
        ).first()
        if coupon_obj:
            if coupon_obj.type == "percent":
                coupon_discount = (subtotal * coupon_obj.value).quantize(Decimal("1"))
            else:
                coupon_discount = coupon_obj.value

    total = subtotal - coupon_discount

    # 驗證付款總額
    payment_total = sum(p.amount for p in payload.payments)
    if abs(float(payment_total - total)) > 0.01:
        raise api_error(
            400,
            "PAYMENT_TOTAL_MISMATCH",
            "Payment total does not match order total",
            {"payment_total": float(payment_total), "order_total": float(total)},
        )

    points_earned = 0
    with db.begin_nested():
        # 建立 Booking：未帶 customer_id 時使用「現場客」避免 FK 壞掉
        booking_customer_id = payload.customer_id
        if booking_customer_id is None:
            walk_in = db.query(Customer).filter(Customer.phone == "WALK-IN").first()
            if not walk_in:
                walk_in = Customer(name="現場客", phone="WALK-IN")
                db.add(walk_in)
                db.flush()
            booking_customer_id = walk_in.id

        booking = Booking(customer_id=booking_customer_id, status=BookingStatus.done)
        db.add(booking)
        db.flush()

        now = datetime.utcnow()
        from datetime import timedelta

        # BookingItems + Commissions
        for item in payload.items:
            if item.type == "service":
                service = db.get(Service, item.item_id)
                if not service:
                    raise api_error(404, "SERVICE_NOT_FOUND", "Service not found", {"service_id": item.item_id})
                end_at = now + timedelta(minutes=int(service.duration))
                db.add(BookingItem(
                    booking_id=booking.id, service_id=service.id,
                    staff_id=item.staff_id, start_at=now, end_at=end_at, price=item.price,
                ))
                item_name = service.name
            else:
                product = db.get(Product, item.item_id)
                if not product:
                    raise api_error(404, "PRODUCT_NOT_FOUND", "Product not found", {"product_id": item.item_id})
                if product.stock < 1:
                    raise api_error(
                        400,
                        "INSUFFICIENT_STOCK",
                        "Product stock is insufficient",
                        {"product_id": item.item_id, "product_name": product.name},
                    )
                product.stock -= 1
                item_name = product.name

            # 抽成記錄
            staff = db.get(Staff, item.staff_id)
            if staff:
                rate = Decimal(str(staff.commission_rate))
                # 指定技師加成 5%
                effective_rate = rate + (Decimal("5") if item.is_designated else Decimal("0"))
                db.add(Commission(
                    booking_id=booking.id, staff_id=item.staff_id,
                    type=item.type, item_name=item_name,
                    is_designated=item.is_designated,
                    base_amount=item.price,
                    commission_rate=effective_rate,
                    commission_amount=(item.price * effective_rate / Decimal("100")).quantize(Decimal("1")),
                ))

        # 付款記錄
        for p in payload.payments:
            db.add(Payment(booking_id=booking.id, method=p.method, amount=p.amount))

        # 優惠券核銷
        if coupon_obj:
            coupon_obj.used_count += 1
            db.add(CouponUsage(
                coupon_id=coupon_obj.id, booking_id=booking.id,
                customer_id=payload.customer_id, discount_amount=coupon_discount,
            ))

        # 更新顧客
        if payload.customer_id:
            customer = db.get(Customer, payload.customer_id)
            if customer:
                customer.total_spent += total
                customer.visits += 1
                customer.last_visit_at = now
                points_earned = int(total // 10)
                customer.points += points_earned
                # 扣除儲值金
                store_value_paid = sum(p.amount for p in payload.payments if p.method == "store_value")
                if store_value_paid > 0:
                    customer.balance -= store_value_paid
                if customer.total_spent >= 50000:
                    customer.level = 'VIP'
                elif customer.total_spent >= 15000:
                    customer.level = '黃金'

    db.commit()
    db.refresh(booking)
    asyncio.create_task(manager.broadcast("booking_created", {"booking_id": booking.id}))
    audit_event(
        "checkout.submit",
        actor_id=getattr(user, "id", None),
        actor_role=getattr(user, "role", None),
        booking_id=booking.id,
        customer_id=booking.customer_id,
        total=float(total),
        item_count=len(payload.items),
        payment_count=len(payload.payments),
    )

    return CheckoutResponse(
        booking_id=booking.id,
        subtotal=subtotal,
        coupon_discount=coupon_discount,
        total=total,
        points_earned=points_earned,
        payments=payload.payments,
    )
