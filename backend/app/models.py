from sqlalchemy import Column,Integer,String,Float,DateTime,ForeignKey,Text,Boolean
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True)
    username=Column(String(50),unique=True)
    password_hash=Column(String(255))
    role=Column(String(30))

class Product(Base):
    __tablename__="products"
    id=Column(Integer,primary_key=True)
    name=Column(String(120),unique=True,nullable=False)
    code=Column(String(50),default="")
    category=Column(String(80),default="Outros")
    description=Column(Text,default="")
    image_url=Column(Text,default="")
    cost=Column(Float,default=0)
    price=Column(Float,default=0)
    stock=Column(Float,default=0)
    min_stock=Column(Float,default=10)
    unit=Column(String(30),default="un")
    sector=Column(String(50),default="Bar")
    printer=Column(String(50),default="Nenhuma")
    track_stock=Column(Boolean,default=True)
    active=Column(Boolean,default=True)
    created_at=Column(DateTime(timezone=True),server_default=func.now())

class TableOrder(Base):
    __tablename__="tables";id=Column(Integer,primary_key=True);name=Column(String(60));customer_name=Column(String(120),default="");status=Column(String(30),default="open");opened_at=Column(DateTime(timezone=True),server_default=func.now())
class Comanda(Base):
    __tablename__="comandas"
    id=Column(Integer,primary_key=True)
    table_id=Column(Integer,ForeignKey("tables.id"),nullable=False)
    name=Column(String(60),default="Comanda 01")
    customer_name=Column(String(120),default="")
    status=Column(String(30),default="open")
    opened_at=Column(DateTime(timezone=True),server_default=func.now())
    closed_at=Column(DateTime(timezone=True),nullable=True)

class OrderItem(Base):
    __tablename__="order_items"
    id=Column(Integer,primary_key=True)
    table_id=Column(Integer,ForeignKey("tables.id"))
    comanda_id=Column(Integer,ForeignKey("comandas.id"),nullable=True)
    product_id=Column(Integer,ForeignKey("products.id"))
    product_name=Column(String(120))
    qty=Column(Float)
    unit_price=Column(Float)
    unit_cost=Column(Float)
    sector=Column(String(50))
    note=Column(Text,default="")
    status=Column(String(30),default="waiting")
    paid=Column(Boolean,default=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
class Sale(Base):
    __tablename__="sales";id=Column(Integer,primary_key=True);origin=Column(String(30),default="table");reference=Column(String(120),default="");total=Column(Float);cost_total=Column(Float);payment_method=Column(String(40));created_at=Column(DateTime(timezone=True),server_default=func.now())
class StockMovement(Base):
    __tablename__="stock_movements";id=Column(Integer,primary_key=True);product_id=Column(Integer,ForeignKey("products.id"));product_name=Column(String(120));movement_type=Column(String(40));qty=Column(Float);note=Column(Text,default="");created_at=Column(DateTime(timezone=True),server_default=func.now())
class Customer(Base):
    __tablename__="customers";id=Column(Integer,primary_key=True);name=Column(String(120));phone=Column(String(40),unique=True);points=Column(Integer,default=0);visits=Column(Integer,default=0);total_spent=Column(Float,default=0)
class Reservation(Base):
    __tablename__="reservations";id=Column(Integer,primary_key=True);customer_name=Column(String(120));phone=Column(String(40));date=Column(String(20));time=Column(String(10));people=Column(Integer,default=2);table_name=Column(String(60),default="");status=Column(String(30),default="confirmed")
class Expense(Base):
    __tablename__="expenses";id=Column(Integer,primary_key=True);description=Column(String(180));category=Column(String(80),default="Outros");amount=Column(Float);status=Column(String(30),default="pending");created_at=Column(DateTime(timezone=True),server_default=func.now())
class AuditLog(Base):
    __tablename__="audit_logs";id=Column(Integer,primary_key=True);username=Column(String(60));action=Column(String(120));detail=Column(Text,default="");created_at=Column(DateTime(timezone=True),server_default=func.now())


class CashSession(Base):
    __tablename__="cash_sessions"
    id=Column(Integer,primary_key=True)
    opened_by=Column(String(60))
    opening_amount=Column(Float,default=0)
    status=Column(String(20),default="open")
    opened_at=Column(DateTime(timezone=True),server_default=func.now())
    closed_at=Column(DateTime(timezone=True),nullable=True)
    counted_amount=Column(Float,nullable=True)
    expected_amount=Column(Float,nullable=True)
    difference=Column(Float,nullable=True)

class CashMovement(Base):
    __tablename__="cash_movements"
    id=Column(Integer,primary_key=True)
    session_id=Column(Integer,ForeignKey("cash_sessions.id"))
    movement_type=Column(String(30))
    amount=Column(Float)
    note=Column(Text,default="")
    username=Column(String(60))
    created_at=Column(DateTime(timezone=True),server_default=func.now())


class PrintJob(Base):
    __tablename__="print_jobs"
    id=Column(Integer,primary_key=True)
    order_item_id=Column(Integer,ForeignKey("order_items.id"))
    sector=Column(String(50))
    status=Column(String(20),default="pending")
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    printed_at=Column(DateTime(timezone=True),nullable=True)

class FinancialEntry(Base):
    __tablename__="financial_entries"
    id=Column(Integer,primary_key=True)
    entry_type=Column(String(20),default="expense")
    description=Column(String(180),nullable=False)
    category=Column(String(80),default="Outros")
    supplier=Column(String(120),default="")
    amount=Column(Float,default=0)
    due_date=Column(String(20),default="")
    payment_method=Column(String(40),default="")
    status=Column(String(30),default="pending")
    recurrence=Column(String(30),default="none")
    notes=Column(Text,default="")
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    paid_at=Column(DateTime(timezone=True),nullable=True)


class StockSupplier(Base):
    __tablename__="stock_suppliers"
    id=Column(Integer,primary_key=True)
    name=Column(String(140),nullable=False)
    contact=Column(String(100),default="")
    phone=Column(String(40),default="")
    notes=Column(Text,default="")
    active=Column(Boolean,default=True)
    created_at=Column(DateTime(timezone=True),server_default=func.now())

class PurchaseOrder(Base):
    __tablename__="purchase_orders"
    id=Column(Integer,primary_key=True)
    supplier_id=Column(Integer,ForeignKey("stock_suppliers.id"),nullable=True)
    supplier_name=Column(String(140),default="")
    status=Column(String(30),default="draft")
    expected_date=Column(String(20),default="")
    notes=Column(Text,default="")
    total=Column(Float,default=0)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    received_at=Column(DateTime(timezone=True),nullable=True)

class PurchaseOrderItem(Base):
    __tablename__="purchase_order_items"
    id=Column(Integer,primary_key=True)
    purchase_order_id=Column(Integer,ForeignKey("purchase_orders.id"))
    product_id=Column(Integer,ForeignKey("products.id"))
    product_name=Column(String(140),default="")
    qty=Column(Float,default=0)
    unit_cost=Column(Float,default=0)
    received_qty=Column(Float,default=0)
