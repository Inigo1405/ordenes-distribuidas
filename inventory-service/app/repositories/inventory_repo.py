from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Product


async def get_product(session: AsyncSession, sku: str) -> Product | None:
    result = await session.execute(select(Product).where(Product.sku == sku))
    return result.scalar()


async def deduct_stock(session: AsyncSession, sku: str, qty: int) -> dict:
    """
    Descuenta qty unidades del SKU.
    Retorna dict con resultado: ok, sku, remaining o error/reason.
    """
    product = await get_product(session, sku)

    if product is None:
        return {"ok": False, "sku": sku, "reason": "SKU no encontrado"}

    if product.stock < qty:
        return {
            "ok": False,
            "sku": sku,
            "reason": f"Stock insuficiente: disponible={product.stock}, solicitado={qty}"
        }

    product.stock -= qty
    await session.commit()

    return {"ok": True, "sku": sku, "remaining": product.stock}


async def seed_products(session: AsyncSession):
    """Inserta productos de ejemplo si la tabla está vacía."""
    result = await session.execute(select(Product))
    if result.scalars().first() is not None:
        return

    products = [
        Product(sku="A1", name="Producto A1", stock=100),
        Product(sku="B2", name="Producto B2", stock=50),
        Product(sku="C3", name="Producto C3", stock=20),
    ]
    session.add_all(products)
    await session.commit()
