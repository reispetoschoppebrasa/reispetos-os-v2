import os
from datetime import datetime,timedelta
from typing import Optional
from fastapi import FastAPI,Depends,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func,text
from .database import Base,engine,get_db,SessionLocal
from .models import *
from .security import hash_password,verify_password,create_token,current_user

app=FastAPI(title="REI'SPETOS OS API",version="1.9.0")
front=os.getenv("FRONTEND_URL","*")
app.add_middleware(CORSMiddleware,allow_origins=["*"] if front=="*" else [front],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

class LoginIn(BaseModel): username:str;password:str
class ProductIn(BaseModel):
    name:str
    code:str=""
    category:str="Outros"
    description:str=""
    image_url:str=""
    cost:float=0
    price:float=0
    stock:float=0
    min_stock:float=10
    unit:str="un"
    sector:str="Bar"
    printer:str="Nenhuma"
    track_stock:bool=True
    active:bool=True
class ProductUpdate(BaseModel):
    name:Optional[str]=None;code:Optional[str]=None;category:Optional[str]=None;description:Optional[str]=None;image_url:Optional[str]=None
    cost:Optional[float]=None;price:Optional[float]=None;stock:Optional[float]=None;min_stock:Optional[float]=None;unit:Optional[str]=None
    sector:Optional[str]=None;printer:Optional[str]=None;track_stock:Optional[bool]=None;active:Optional[bool]=None
class ProductStockIn(BaseModel): qty:float;movement_type:str="adjustment";note:str=""
class TableIn(BaseModel): name:str;customer_name:str=""
class ComandaIn(BaseModel): name:str="";customer_name:str=""
class ItemIn(BaseModel): product_id:int;qty:float;note:str=""
class ItemUpdate(BaseModel): qty:Optional[float]=None;note:Optional[str]=None
class CloseIn(BaseModel): payment_method:str
class StockIn(BaseModel): product_id:int;movement_type:str;qty:float;note:str=""

class CashOpenIn(BaseModel): opening_amount:float=0
class CashMoveIn(BaseModel): movement_type:str;amount:float;note:str=""
class CashCloseIn(BaseModel): counted_amount:float

class CustomerIn(BaseModel): name:str;phone:str
class ReservationIn(BaseModel): customer_name:str;phone:str;date:str;time:str;people:int=2;table_name:str=""
class ExpenseIn(BaseModel): description:str;category:str="Outros";amount:float;status:str="pending"

def audit(db,u,a,d=""): db.add(AuditLog(username=u["username"],action=a,detail=d))

def migrate_products():
    """Adiciona campos novos sem apagar dados do MVP já publicado."""
    wanted={
        "code":"VARCHAR(50) DEFAULT ''","category":"VARCHAR(80) DEFAULT 'Outros'","description":"TEXT DEFAULT ''",
        "image_url":"TEXT DEFAULT ''","unit":"VARCHAR(30) DEFAULT 'un'","printer":"VARCHAR(50) DEFAULT 'Nenhuma'",
        "track_stock":"BOOLEAN DEFAULT 1","created_at":"DATETIME"
    }
    with engine.begin() as conn:
        try:
            rows=conn.execute(text("PRAGMA table_info(products)")).fetchall()
            existing={r[1] for r in rows}
            for name,kind in wanted.items():
                if name not in existing: conn.execute(text(f"ALTER TABLE products ADD COLUMN {name} {kind}"))
        except Exception:
            # PostgreSQL / outros bancos
            for name,kind in wanted.items():
                pg_kind=kind.replace("DATETIME","TIMESTAMP").replace("BOOLEAN DEFAULT 1","BOOLEAN DEFAULT TRUE")
                try: conn.execute(text(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {name} {pg_kind}"))
                except Exception: pass

def migrate_comandas():
    """Atualiza o banco existente sem apagar mesas, pedidos ou vendas."""
    with engine.begin() as conn:
        try:
            rows=conn.execute(text("PRAGMA table_info(order_items)")).fetchall()
            existing={r[1] for r in rows}
            if "comanda_id" not in existing: conn.execute(text("ALTER TABLE order_items ADD COLUMN comanda_id INTEGER"))
            if "paid" not in existing: conn.execute(text("ALTER TABLE order_items ADD COLUMN paid BOOLEAN DEFAULT 0"))
        except Exception:
            for stmt in [
                "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS comanda_id INTEGER",
                "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS paid BOOLEAN DEFAULT FALSE"
            ]:
                try: conn.execute(text(stmt))
                except Exception: pass

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine);migrate_products();migrate_comandas();db=SessionLocal()
    try:
        if not db.query(User).filter_by(username="admin").first(): db.add(User(username="admin",password_hash=hash_password("1234"),role="admin"))
        if not db.query(User).filter_by(username="caixa").first(): db.add(User(username="caixa",password_hash=hash_password("0000"),role="caixa"))
        if db.query(Product).count()==0:
            db.add_all([
                Product(name="Heineken",category="Cervejas",cost=6.19,price=12,stock=72,min_stock=20,unit="garrafa",sector="Bar"),
                Product(name="Brahma/Skol",category="Cervejas",cost=2.65,price=8,stock=80,min_stock=20,unit="garrafa",sector="Bar"),
                Product(name="Original",category="Cervejas",cost=3.3,price=7,stock=60,min_stock=20,unit="garrafa",sector="Bar"),
                Product(name="Espeto de Carne",category="Espetos",cost=4.5,price=8,stock=100,min_stock=20,unit="espeto",sector="Churrasqueira"),
                Product(name="Chopp 500ml",category="Chopp",cost=3.8,price=10,stock=200,min_stock=30,unit="copo",sector="Bar"),
                Product(name="Batata Frita",category="Porções",cost=7,price=24,stock=30,min_stock=10,unit="porção",sector="Cozinha")
            ])
        db.commit()
    finally: db.close()

@app.get("/health")
def health(): return {"ok":True,"system":"REI'SPETOS OS","version":"1.9.0"}
@app.post("/auth/login")
def login(p:LoginIn,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=p.username.lower().strip()).first()
    if not u or not verify_password(p.password,u.password_hash): raise HTTPException(401,"Usuário ou senha inválidos")
    return {"token":create_token(u.username,u.role),"username":u.username,"role":u.role}
@app.get("/dashboard")
def dashboard(u=Depends(current_user),db:Session=Depends(get_db)):
    r=float(db.query(func.coalesce(func.sum(Sale.total),0)).scalar() or 0);c=float(db.query(func.coalesce(func.sum(Sale.cost_total),0)).scalar() or 0);e=float(db.query(func.coalesce(func.sum(Expense.amount),0)).filter(Expense.status=="paid").scalar() or 0)
    return {"revenue":r,"cost":c,"expenses":e,"profit":r-c-e,"low_stock":db.query(Product).filter(Product.active==True,Product.track_stock==True,Product.stock<=Product.min_stock).count(),"open_tables":db.query(TableOrder).filter(TableOrder.status=="open").count(),"products":db.query(Product).filter(Product.active==True).count()}


@app.get("/reports/summary")
def report_summary(days:int=30,u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    days=max(1,min(days,365))
    start=datetime.utcnow()-timedelta(days=days)
    sales=db.query(Sale).filter(Sale.created_at>=start).all()
    revenue=sum(float(x.total or 0) for x in sales)
    cost=sum(float(x.cost_total or 0) for x in sales)
    paid_expenses=float(db.query(func.coalesce(func.sum(Expense.amount),0)).filter(Expense.status=="paid",Expense.created_at>=start).scalar() or 0)
    profit=revenue-cost-paid_expenses
    ticket=(revenue/len(sales)) if sales else 0

    payments={}
    for s in sales:
        key=s.payment_method or "Não informado"
        payments[key]=payments.get(key,0)+float(s.total or 0)

    top_rows=db.query(
        OrderItem.product_name,
        func.sum(OrderItem.qty).label("qty"),
        func.sum(OrderItem.qty*OrderItem.unit_price).label("revenue"),
        func.sum(OrderItem.qty*OrderItem.unit_cost).label("cost")
    ).filter(OrderItem.paid==True,OrderItem.created_at>=start).group_by(OrderItem.product_name).order_by(func.sum(OrderItem.qty).desc()).limit(10).all()

    daily={}
    for s in sales:
        key=s.created_at.strftime("%Y-%m-%d") if s.created_at else ""
        if key:
            daily[key]=daily.get(key,0)+float(s.total or 0)

    return {
        "period_days":days,
        "sales_count":len(sales),
        "revenue":revenue,
        "cost":cost,
        "expenses":paid_expenses,
        "profit":profit,
        "margin":(profit/revenue*100) if revenue else 0,
        "ticket_average":ticket,
        "payments":[{"name":k,"value":v} for k,v in sorted(payments.items(),key=lambda x:x[1],reverse=True)],
        "top_products":[{"name":r.product_name,"qty":float(r.qty or 0),"revenue":float(r.revenue or 0),"profit":float((r.revenue or 0)-(r.cost or 0))} for r in top_rows],
        "daily":[{"date":k,"value":daily[k]} for k in sorted(daily.keys())]
    }

@app.get("/products")
def products(u=Depends(current_user),db:Session=Depends(get_db)): return db.query(Product).order_by(Product.active.desc(),Product.name).all()
@app.post("/products")
def add_product(p:ProductIn,u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    if db.query(Product).filter(func.lower(Product.name)==p.name.lower().strip()).first(): raise HTTPException(409,"Já existe um produto com esse nome")
    x=Product(**p.model_dump());x.name=x.name.strip();db.add(x);db.flush()
    if x.stock: db.add(StockMovement(product_id=x.id,product_name=x.name,movement_type="initial",qty=x.stock,note="Estoque inicial"))
    audit(db,u,"Produto criado",x.name);db.commit();db.refresh(x);return x
@app.put("/products/{pid}")
def update_product(pid:int,p:ProductUpdate,u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    x=db.get(Product,pid)
    if not x: raise HTTPException(404,"Produto não encontrado")
    changes=p.model_dump(exclude_unset=True);old_stock=x.stock
    if "name" in changes: changes["name"]=changes["name"].strip()
    for k,v in changes.items(): setattr(x,k,v)
    if "stock" in changes and x.stock!=old_stock: db.add(StockMovement(product_id=x.id,product_name=x.name,movement_type="adjustment",qty=x.stock-old_stock,note="Alteração no cadastro"))
    audit(db,u,"Produto alterado",x.name);db.commit();db.refresh(x);return x
@app.delete("/products/{pid}")
def deactivate_product(pid:int,u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    x=db.get(Product,pid)
    if not x: raise HTTPException(404,"Produto não encontrado")
    x.active=False;audit(db,u,"Produto desativado",x.name);db.commit();return {"ok":True}
@app.post("/products/{pid}/stock")
def adjust_product_stock(pid:int,p:ProductStockIn,u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    x=db.get(Product,pid)
    if not x: raise HTTPException(404,"Produto não encontrado")
    if x.stock+p.qty<0: raise HTTPException(400,"O ajuste deixaria o estoque negativo")
    x.stock+=p.qty;db.add(StockMovement(product_id=x.id,product_name=x.name,movement_type=p.movement_type,qty=p.qty,note=p.note));audit(db,u,"Estoque ajustado",f"{x.name}: {p.qty:+g}");db.commit();db.refresh(x);return x
@app.get("/products/{pid}/movements")
def product_movements(pid:int,u=Depends(current_user),db:Session=Depends(get_db)): return db.query(StockMovement).filter(StockMovement.product_id==pid).order_by(StockMovement.id.desc()).limit(100).all()

@app.get("/tables")
def tables(u=Depends(current_user),db:Session=Depends(get_db)):
    physical=[f"Mesa {i:02d}" for i in range(1,21)]+[f"Bistrô {i:02d}" for i in range(1,5)]
    open_rows={t.name:t for t in db.query(TableOrder).filter(TableOrder.status=="open").all()}
    out=[]
    for name in physical:
        t=open_rows.get(name)
        if not t:
            out.append({"id":None,"name":name,"status":"free","customer_name":"","total":0,"comandas":[]})
            continue
        comandas=[]
        rows=db.query(Comanda).filter(Comanda.table_id==t.id).order_by(Comanda.id).all()
        # Migra pedidos antigos para uma comanda padrão na primeira abertura da tela.
        legacy=db.query(OrderItem).filter(OrderItem.table_id==t.id,OrderItem.comanda_id==None).count()
        if legacy and not rows:
            c=Comanda(table_id=t.id,name="Comanda 01",customer_name=t.customer_name or "Cliente",status="open")
            db.add(c);db.flush()
            db.query(OrderItem).filter(OrderItem.table_id==t.id,OrderItem.comanda_id==None).update({OrderItem.comanda_id:c.id})
            db.commit();rows=[c]
        for c in rows:
            items=db.query(OrderItem).filter(OrderItem.comanda_id==c.id).order_by(OrderItem.id).all()
            comandas.append({"id":c.id,"name":c.name,"customer_name":c.customer_name,"status":c.status,"total":sum(i.qty*i.unit_price for i in items if not i.paid),"items":items})
        out.append({"id":t.id,"name":t.name,"status":"open","customer_name":t.customer_name,"total":sum(c["total"] for c in comandas),"comandas":comandas})
    return out

@app.post("/tables")
def open_table(p:TableIn,u=Depends(current_user),db:Session=Depends(get_db)):
    if db.query(TableOrder).filter(TableOrder.name==p.name,TableOrder.status=="open").first(): raise HTTPException(409,"Mesa já aberta")
    t=TableOrder(name=p.name,customer_name=p.customer_name,status="open");db.add(t);db.flush()
    c=Comanda(table_id=t.id,name="Comanda 01",customer_name=p.customer_name or "Cliente",status="open");db.add(c)
    audit(db,u,"Mesa aberta",p.name);db.commit();db.refresh(t);return {"table_id":t.id,"comanda_id":c.id}

@app.post("/tables/{tid}/comandas")
def add_comanda(tid:int,p:ComandaIn,u=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(TableOrder,tid)
    if not t or t.status!="open": raise HTTPException(404,"Mesa não encontrada")
    n=db.query(Comanda).filter(Comanda.table_id==tid).count()+1
    c=Comanda(table_id=tid,name=p.name.strip() or f"Comanda {n:02d}",customer_name=p.customer_name.strip() or f"Cliente {n}",status="open")
    db.add(c);audit(db,u,"Comanda criada",f"{t.name} - {c.customer_name}");db.commit();db.refresh(c);return c

@app.post("/comandas/{cid}/items")
def add_comanda_item(cid:int,p:ItemIn,u=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Comanda,cid);pr=db.get(Product,p.product_id)
    if not c or c.status!="open": raise HTTPException(404,"Comanda não encontrada")
    t=db.get(TableOrder,c.table_id)
    if not t or t.status!="open": raise HTTPException(404,"Mesa não encontrada")
    if not pr or not pr.active: raise HTTPException(404,"Produto não encontrado")
    if p.qty<=0: raise HTTPException(400,"Quantidade inválida")
    if pr.track_stock and pr.stock<p.qty: raise HTTPException(400,"Estoque insuficiente")
    if pr.track_stock:
        pr.stock-=p.qty;db.add(StockMovement(product_id=pr.id,product_name=pr.name,movement_type="sale",qty=-p.qty,note=f"{t.name} / {c.customer_name}"))
    i=OrderItem(table_id=t.id,comanda_id=c.id,product_id=pr.id,product_name=pr.name,qty=p.qty,unit_price=pr.price,unit_cost=pr.cost,sector=pr.sector,note=p.note,status="waiting",paid=False)
    db.add(i);db.flush()
    db.add(PrintJob(order_item_id=i.id,sector=pr.sector,status="pending"))
    audit(db,u,"Item lançado",f"{t.name} / {c.customer_name} - {p.qty}x {pr.name}")
    db.commit();db.refresh(i);return i

@app.put("/items/{iid}")
def update_item(iid:int,p:ItemUpdate,u=Depends(current_user),db:Session=Depends(get_db)):
    i=db.get(OrderItem,iid)
    if not i or i.paid: raise HTTPException(404,"Item não encontrado")
    if p.qty is not None:
        if p.qty<=0: raise HTTPException(400,"Quantidade inválida")
        diff=p.qty-i.qty
        pr=db.get(Product,i.product_id)
        if pr and pr.track_stock:
            if diff>0 and pr.stock<diff: raise HTTPException(400,"Estoque insuficiente")
            pr.stock-=diff
            db.add(StockMovement(product_id=pr.id,product_name=pr.name,movement_type="item_edit",qty=-diff,note="Alteração de quantidade"))
        i.qty=p.qty
    if p.note is not None: i.note=p.note.strip()
    audit(db,u,"Item editado",f"{i.qty}x {i.product_name}")
    db.commit();db.refresh(i);return i

@app.post("/items/{iid}/duplicate")
def duplicate_item(iid:int,u=Depends(current_user),db:Session=Depends(get_db)):
    i=db.get(OrderItem,iid)
    if not i or i.paid: raise HTTPException(404,"Item não encontrado")
    return add_comanda_item(i.comanda_id,ItemIn(product_id=i.product_id,qty=i.qty,note=i.note),u,db)

@app.delete("/items/{iid}")
def cancel_item(iid:int,u=Depends(current_user),db:Session=Depends(get_db)):
    i=db.get(OrderItem,iid)
    if not i or i.paid: raise HTTPException(404,"Item não encontrado")
    pr=db.get(Product,i.product_id)
    if pr and pr.track_stock:
        pr.stock+=i.qty;db.add(StockMovement(product_id=pr.id,product_name=pr.name,movement_type="cancel",qty=i.qty,note="Cancelamento de item"))
    audit(db,u,"Item cancelado",f"{i.qty}x {i.product_name}");db.delete(i);db.commit();return {"ok":True}

@app.post("/comandas/{cid}/close")
def close_comanda(cid:int,p:CloseIn,u=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Comanda,cid)
    if not c or c.status!="open": raise HTTPException(404,"Comanda não encontrada")
    t=db.get(TableOrder,c.table_id)
    items=db.query(OrderItem).filter(OrderItem.comanda_id==cid,OrderItem.paid==False).all()
    if not items: raise HTTPException(400,"Comanda sem itens")
    total=sum(i.qty*i.unit_price for i in items);cost=sum(i.qty*i.unit_cost for i in items)
    db.add(Sale(origin="comanda",reference=f"{t.name} / {c.customer_name}",total=total,cost_total=cost,payment_method=p.payment_method))
    for i in items: i.paid=True;i.status="delivered" if i.status!="delivered" else i.status
    c.status="closed";c.closed_at=datetime.utcnow()
    if db.query(Comanda).filter(Comanda.table_id==t.id,Comanda.status=="open",Comanda.id!=c.id).count()==0: t.status="closed"
    audit(db,u,"Comanda fechada",f"{t.name} / {c.customer_name} - {total:.2f} - {p.payment_method}");db.commit();return {"ok":True,"total":total}


@app.post("/tables/{tid}/transfer")
def transfer_table(tid:int,p:dict,u=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(TableOrder,tid)
    if not t or t.status!="open":
        raise HTTPException(404,"Mesa não encontrada")
    target=str(p.get("target_name","")).strip()
    physical=[f"Mesa {i:02d}" for i in range(1,21)]+[f"Bistrô {i:02d}" for i in range(1,5)]
    if target not in physical:
        raise HTTPException(400,"Destino inválido")
    if target==t.name:
        raise HTTPException(400,"Escolha outra mesa")
    if db.query(TableOrder).filter(TableOrder.name==target,TableOrder.status=="open").first():
        raise HTTPException(409,"A mesa de destino já está ocupada")
    old=t.name
    t.name=target
    audit(db,u,"Mesa transferida",f"{old} → {target}")
    db.commit()
    return {"ok":True,"from":old,"to":target}

# Compatibilidade com o MVP anterior.
@app.post("/tables/{tid}/items")
def add_item(tid:int,p:ItemIn,u=Depends(current_user),db:Session=Depends(get_db)):
    c=db.query(Comanda).filter(Comanda.table_id==tid,Comanda.status=="open").order_by(Comanda.id).first()
    if not c: raise HTTPException(404,"Comanda não encontrada")
    return add_comanda_item(c.id,p,u,db)

@app.post("/tables/{tid}/close")
def close_table(tid:int,p:CloseIn,u=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(TableOrder,tid)
    if not t or t.status!="open": raise HTTPException(404,"Mesa não encontrada")
    comandas=db.query(Comanda).filter(Comanda.table_id==tid,Comanda.status=="open").all()
    total=0
    for c in comandas:
        items=db.query(OrderItem).filter(OrderItem.comanda_id==c.id,OrderItem.paid==False).all()
        if not items: c.status="closed";continue
        subtotal=sum(i.qty*i.unit_price for i in items);cost=sum(i.qty*i.unit_cost for i in items);total+=subtotal
        db.add(Sale(origin="table",reference=f"{t.name} / {c.customer_name}",total=subtotal,cost_total=cost,payment_method=p.payment_method))
        for i in items: i.paid=True;i.status="delivered"
        c.status="closed";c.closed_at=datetime.utcnow()
    t.status="closed";audit(db,u,"Mesa fechada",f"{t.name} - {total:.2f}");db.commit();return {"ok":True,"total":total}

@app.get("/production")
def production(u=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(OrderItem).filter(OrderItem.status!="delivered",OrderItem.paid==False).order_by(OrderItem.created_at,OrderItem.id).all()
    out=[]
    for i in rows:
        t=db.get(TableOrder,i.table_id)
        c=db.get(Comanda,i.comanda_id) if i.comanda_id else None
        out.append({
            "id":i.id,"table_id":i.table_id,"table_name":t.name if t else "Mesa",
            "comanda_id":i.comanda_id,"customer_name":c.customer_name if c else (t.customer_name if t else "Cliente"),
            "product_id":i.product_id,"product_name":i.product_name,"qty":i.qty,"unit_price":i.unit_price,
            "sector":i.sector,"note":i.note,"status":i.status,"created_at":i.created_at
        })
    return out

@app.get("/print-jobs")
def print_jobs(sector:Optional[str]=None,u=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(PrintJob).filter(PrintJob.status=="pending")
    if sector: q=q.filter(PrintJob.sector==sector)
    jobs=q.order_by(PrintJob.created_at,PrintJob.id).all()
    out=[]
    for j in jobs:
        i=db.get(OrderItem,j.order_item_id)
        if not i or i.paid or i.status=="delivered":
            j.status="ignored"
            continue
        t=db.get(TableOrder,i.table_id)
        c=db.get(Comanda,i.comanda_id) if i.comanda_id else None
        out.append({
            "id":j.id,"order_item_id":i.id,"sector":j.sector,
            "table_name":t.name if t else "Mesa",
            "customer_name":c.customer_name if c else (t.customer_name if t else "Cliente"),
            "product_name":i.product_name,"qty":i.qty,"note":i.note,
            "created_at":j.created_at
        })
    db.commit()
    return out

@app.post("/print-jobs/{jid}/printed")
def mark_printed(jid:int,u=Depends(current_user),db:Session=Depends(get_db)):
    j=db.get(PrintJob,jid)
    if not j: raise HTTPException(404,"Impressão não encontrada")
    j.status="printed";j.printed_at=datetime.utcnow()
    db.commit()
    return {"ok":True}

@app.post("/production/{iid}/reprint")
def reprint_item(iid:int,u=Depends(current_user),db:Session=Depends(get_db)):
    i=db.get(OrderItem,iid)
    if not i: raise HTTPException(404,"Pedido não encontrado")
    j=PrintJob(order_item_id=i.id,sector=i.sector,status="pending")
    db.add(j);audit(db,u,"Reimpressão solicitada",f"{i.product_name} - {i.sector}")
    db.commit();db.refresh(j)
    return {"ok":True,"print_job_id":j.id}

@app.post("/production/{iid}/{status}")
def prod_status(iid:int,status:str,u=Depends(current_user),db:Session=Depends(get_db)):
    i=db.get(OrderItem,iid)
    if not i: raise HTTPException(404,"Pedido não encontrado")
    if status not in ["waiting","preparing","ready","delivered"]: raise HTTPException(400,"Status inválido")
    i.status=status;audit(db,u,"Status de produção",f"{i.product_name} - {status}");db.commit();return {"ok":True}

def _cash_payload(db:Session,s):
    if not s:
        return {"open":False,"session":None,"movements":[],"sales_total":0,"expected_amount":0}
    sales_total=float(db.query(func.coalesce(func.sum(Sale.total),0)).filter(Sale.created_at>=s.opened_at).scalar() or 0)
    moves=db.query(CashMovement).filter(CashMovement.session_id==s.id).order_by(CashMovement.id.desc()).all()
    supplies=sum(float(x.amount or 0) for x in moves if x.movement_type=="supply")
    withdrawals=sum(float(x.amount or 0) for x in moves if x.movement_type in ("withdrawal","expense"))
    expected=float(s.opening_amount or 0)+sales_total+supplies-withdrawals
    return {
        "open":s.status=="open",
        "session":s,
        "movements":moves,
        "sales_total":sales_total,
        "supplies":supplies,
        "withdrawals":withdrawals,
        "expected_amount":expected
    }

@app.get("/cash/status")
def cash_status(u=Depends(current_user),db:Session=Depends(get_db)):
    s=db.query(CashSession).filter(CashSession.status=="open").order_by(CashSession.id.desc()).first()
    return _cash_payload(db,s)

@app.post("/cash/open")
def cash_open(p:CashOpenIn,u=Depends(current_user),db:Session=Depends(get_db)):
    if db.query(CashSession).filter(CashSession.status=="open").first():
        raise HTTPException(409,"Já existe um caixa aberto")
    s=CashSession(opened_by=u["username"],opening_amount=max(0,float(p.opening_amount or 0)),status="open")
    db.add(s);audit(db,u,"Caixa aberto",f"Fundo inicial: R$ {s.opening_amount:.2f}");db.commit();db.refresh(s)
    return _cash_payload(db,s)

@app.post("/cash/movement")
def cash_movement(p:CashMoveIn,u=Depends(current_user),db:Session=Depends(get_db)):
    s=db.query(CashSession).filter(CashSession.status=="open").order_by(CashSession.id.desc()).first()
    if not s: raise HTTPException(409,"Abra o caixa primeiro")
    kind=p.movement_type.strip().lower()
    if kind not in ("supply","withdrawal","expense"): raise HTTPException(400,"Tipo de movimentação inválido")
    amount=float(p.amount or 0)
    if amount<=0: raise HTTPException(400,"Informe um valor maior que zero")
    x=CashMovement(session_id=s.id,movement_type=kind,amount=amount,note=p.note.strip(),username=u["username"])
    db.add(x);audit(db,u,"Movimentação de caixa",f"{kind}: R$ {amount:.2f} — {p.note}");db.commit()
    return _cash_payload(db,s)

@app.post("/cash/close")
def cash_close(p:CashCloseIn,u=Depends(current_user),db:Session=Depends(get_db)):
    s=db.query(CashSession).filter(CashSession.status=="open").order_by(CashSession.id.desc()).first()
    if not s: raise HTTPException(409,"Não existe caixa aberto")
    payload=_cash_payload(db,s)
    s.counted_amount=float(p.counted_amount or 0)
    s.expected_amount=float(payload["expected_amount"])
    s.difference=s.counted_amount-s.expected_amount
    s.status="closed";s.closed_at=datetime.utcnow()
    audit(db,u,"Caixa fechado",f"Esperado: R$ {s.expected_amount:.2f} | Contado: R$ {s.counted_amount:.2f} | Diferença: R$ {s.difference:.2f}")
    db.commit();db.refresh(s)
    return {"ok":True,"session":s}

@app.get("/customers")
def customers(u=Depends(current_user),db:Session=Depends(get_db)): return db.query(Customer).order_by(Customer.name).all()
@app.post("/customers")
def add_customer(p:CustomerIn,u=Depends(current_user),db:Session=Depends(get_db)):
    if db.query(Customer).filter_by(phone=p.phone).first(): raise HTTPException(409,"Telefone já cadastrado")
    c=Customer(name=p.name,phone=p.phone);db.add(c);audit(db,u,"Cliente cadastrado",p.name);db.commit();db.refresh(c);return c
@app.get("/reservations")
def reservations(u=Depends(current_user),db:Session=Depends(get_db)): return db.query(Reservation).order_by(Reservation.id.desc()).all()
@app.post("/reservations")
def add_reservation(p:ReservationIn,u=Depends(current_user),db:Session=Depends(get_db)):
    r=Reservation(**p.model_dump());db.add(r);audit(db,u,"Reserva criada",f"{r.customer_name} {r.date} {r.time}");db.commit();db.refresh(r);return r
@app.get("/expenses")
def expenses(u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    return db.query(Expense).order_by(Expense.id.desc()).all()
@app.post("/expenses")
def add_expense(p:ExpenseIn,u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    e=Expense(**p.model_dump());db.add(e);audit(db,u,"Despesa criada",p.description);db.commit();db.refresh(e);return e
@app.get("/audit")
def logs(u=Depends(current_user),db:Session=Depends(get_db)):
    if u["role"]!="admin": raise HTTPException(403,"Apenas administrador")
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()
