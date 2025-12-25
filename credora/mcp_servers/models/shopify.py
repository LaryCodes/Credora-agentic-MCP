"""
Shopify data models.

Data structures for Shopify e-commerce data.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StoreInfo:
    """Shopify store information.
    
    Requirements: 5.1
    
    Attributes:
        id: Unique store identifier
        name: Store display name
        domain: Store domain (e.g., mystore.myshopify.com)
        email: Store contact email
        currency: Store currency code (e.g., USD)
        timezone: Store timezone
        plan_name: Shopify plan name
    """
    
    id: str
    name: str
    domain: str
    email: str
    currency: str
    timezone: str
    plan_name: str
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.name:
            raise ValueError("name is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "email": self.email,
            "currency": self.currency,
            "timezone": self.timezone,
            "plan_name": self.plan_name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoreInfo":
        """Create StoreInfo from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            domain=data.get("domain", ""),
            email=data.get("email", ""),
            currency=data.get("currency", ""),
            timezone=data.get("timezone", ""),
            plan_name=data.get("plan_name", ""),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "StoreInfo":
        """Create StoreInfo from Shopify API response."""
        shop = data.get("shop", data)
        return cls(
            id=str(shop.get("id", "")),
            name=shop.get("name", ""),
            domain=shop.get("domain", shop.get("myshopify_domain", "")),
            email=shop.get("email", ""),
            currency=shop.get("currency", "USD"),
            timezone=shop.get("iana_timezone", shop.get("timezone", "")),
            plan_name=shop.get("plan_name", ""),
        )


@dataclass
class LineItem:
    """Order line item.
    
    Attributes:
        id: Line item identifier
        product_id: Associated product ID
        variant_id: Product variant ID
        title: Product title
        quantity: Quantity ordered
        price: Unit price
    """
    
    id: str
    product_id: str
    variant_id: str
    title: str
    quantity: int
    price: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "title": self.title,
            "quantity": self.quantity,
            "price": self.price,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineItem":
        """Create LineItem from dictionary."""
        return cls(
            id=data.get("id", ""),
            product_id=data.get("product_id", ""),
            variant_id=data.get("variant_id", ""),
            title=data.get("title", ""),
            quantity=int(data.get("quantity", 0)),
            price=float(data.get("price", 0)),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "LineItem":
        """Create LineItem from Shopify API response."""
        return cls(
            id=str(data.get("id", "")),
            product_id=str(data.get("product_id", "")),
            variant_id=str(data.get("variant_id", "")),
            title=data.get("title", ""),
            quantity=int(data.get("quantity", 0)),
            price=float(data.get("price", 0)),
        )


@dataclass
class Order:
    """Shopify order with details.
    
    Requirements: 5.2
    
    Attributes:
        id: Unique order identifier
        order_number: Human-readable order number
        created_at: Order creation timestamp
        total_price: Total order price
        currency: Order currency code
        status: Order fulfillment status
        line_items: List of order line items
        customer_id: Associated customer ID
    """
    
    id: str
    order_number: str
    created_at: datetime
    total_price: float
    currency: str
    status: str
    line_items: List[LineItem] = field(default_factory=list)
    customer_id: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.order_number:
            raise ValueError("order_number is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "total_price": self.total_price,
            "currency": self.currency,
            "status": self.status,
            "line_items": [item.to_dict() for item in self.line_items],
            "customer_id": self.customer_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """Create Order from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        line_items = [
            LineItem.from_dict(item) if isinstance(item, dict) else item
            for item in data.get("line_items", [])
        ]
        
        return cls(
            id=data.get("id", ""),
            order_number=data.get("order_number", ""),
            created_at=created_at,
            total_price=float(data.get("total_price", 0)),
            currency=data.get("currency", ""),
            status=data.get("status", ""),
            line_items=line_items,
            customer_id=data.get("customer_id"),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Order":
        """Create Order from Shopify API response."""
        created_at_str = data.get("created_at", "")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.now()
        
        line_items = [
            LineItem.from_api_response(item)
            for item in data.get("line_items", [])
        ]
        
        # Determine status from fulfillment_status and financial_status
        fulfillment_status = data.get("fulfillment_status") or "unfulfilled"
        financial_status = data.get("financial_status", "pending")
        
        if data.get("cancelled_at"):
            status = "cancelled"
        elif fulfillment_status == "fulfilled":
            status = "fulfilled"
        elif fulfillment_status == "partial":
            status = "partial"
        else:
            status = financial_status
        
        customer = data.get("customer", {})
        customer_id = str(customer.get("id", "")) if customer else None
        
        return cls(
            id=str(data.get("id", "")),
            order_number=str(data.get("order_number", data.get("name", ""))),
            created_at=created_at,
            total_price=float(data.get("total_price", 0)),
            currency=data.get("currency", "USD"),
            status=status,
            line_items=line_items,
            customer_id=customer_id,
        )


@dataclass
class Product:
    """Shopify product with inventory.
    
    Requirements: 5.3
    
    Attributes:
        id: Unique product identifier
        title: Product title
        vendor: Product vendor/brand
        product_type: Product category/type
        status: Product status (active, draft, archived)
        inventory_quantity: Total inventory across all variants
        price: Product price (from first variant)
    """
    
    id: str
    title: str
    vendor: str
    product_type: str
    status: str
    inventory_quantity: int
    price: float
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.title:
            raise ValueError("title is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "vendor": self.vendor,
            "product_type": self.product_type,
            "status": self.status,
            "inventory_quantity": self.inventory_quantity,
            "price": self.price,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """Create Product from dictionary."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            vendor=data.get("vendor", ""),
            product_type=data.get("product_type", ""),
            status=data.get("status", ""),
            inventory_quantity=int(data.get("inventory_quantity", 0)),
            price=float(data.get("price", 0)),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Product":
        """Create Product from Shopify API response."""
        # Calculate total inventory from variants
        variants = data.get("variants", [])
        total_inventory = sum(
            int(v.get("inventory_quantity", 0)) for v in variants
        )
        
        # Get price from first variant
        price = 0.0
        if variants:
            price = float(variants[0].get("price", 0))
        
        return cls(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            vendor=data.get("vendor", ""),
            product_type=data.get("product_type", ""),
            status=data.get("status", "active"),
            inventory_quantity=total_inventory,
            price=price,
        )


@dataclass
class Customer:
    """Shopify customer information.
    
    Requirements: 5.4
    
    Attributes:
        id: Unique customer identifier
        email: Customer email address
        first_name: Customer first name
        last_name: Customer last name
        orders_count: Total number of orders
        total_spent: Total amount spent
        created_at: Customer creation timestamp
        tags: Customer tags for segmentation
    """
    
    id: str
    email: str
    first_name: str
    last_name: str
    orders_count: int
    total_spent: float
    created_at: datetime
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "orders_count": self.orders_count,
            "total_spent": self.total_spent,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        """Create Customer from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        
        return cls(
            id=data.get("id", ""),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            orders_count=int(data.get("orders_count", 0)),
            total_spent=float(data.get("total_spent", 0)),
            created_at=created_at,
            tags=tags,
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Customer":
        """Create Customer from Shopify API response."""
        created_at_str = data.get("created_at", "")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.now()
        
        # Parse tags (Shopify returns comma-separated string)
        tags_str = data.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        
        # Parse total_spent (Shopify returns string)
        total_spent_str = data.get("total_spent", "0")
        total_spent = float(total_spent_str) if total_spent_str else 0.0
        
        return cls(
            id=str(data.get("id", "")),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            orders_count=int(data.get("orders_count", 0)),
            total_spent=total_spent,
            created_at=created_at,
            tags=tags,
        )


@dataclass
class ProductSales:
    """Product sales summary.
    
    Attributes:
        product_id: Product identifier
        title: Product title
        units_sold: Total units sold
        revenue: Total revenue from product
    """
    
    product_id: str
    title: str
    units_sold: int
    revenue: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "product_id": self.product_id,
            "title": self.title,
            "units_sold": self.units_sold,
            "revenue": self.revenue,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductSales":
        """Create ProductSales from dictionary."""
        return cls(
            product_id=data.get("product_id", ""),
            title=data.get("title", ""),
            units_sold=int(data.get("units_sold", 0)),
            revenue=float(data.get("revenue", 0)),
        )


@dataclass
class SalesAnalytics:
    """Sales analytics summary.
    
    Requirements: 5.5
    
    Attributes:
        total_revenue: Total revenue in period
        total_orders: Total number of orders
        average_order_value: Average order value (AOV)
        conversion_rate: Conversion rate percentage
        top_products: List of top selling products
    """
    
    total_revenue: float
    total_orders: int
    average_order_value: float
    conversion_rate: float
    top_products: List[ProductSales] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_revenue": self.total_revenue,
            "total_orders": self.total_orders,
            "average_order_value": self.average_order_value,
            "conversion_rate": self.conversion_rate,
            "top_products": [p.to_dict() for p in self.top_products],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SalesAnalytics":
        """Create SalesAnalytics from dictionary."""
        top_products = [
            ProductSales.from_dict(p) if isinstance(p, dict) else p
            for p in data.get("top_products", [])
        ]
        
        return cls(
            total_revenue=float(data.get("total_revenue", 0)),
            total_orders=int(data.get("total_orders", 0)),
            average_order_value=float(data.get("average_order_value", 0)),
            conversion_rate=float(data.get("conversion_rate", 0)),
            top_products=top_products,
        )
    
    @classmethod
    def from_orders(cls, orders: List["Order"]) -> "SalesAnalytics":
        """Calculate analytics from a list of orders.
        
        Args:
            orders: List of Order objects
            
        Returns:
            SalesAnalytics with calculated metrics
        """
        if not orders:
            return cls(
                total_revenue=0.0,
                total_orders=0,
                average_order_value=0.0,
                conversion_rate=0.0,
                top_products=[],
            )
        
        total_revenue = sum(o.total_price for o in orders)
        total_orders = len(orders)
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
        
        # Calculate top products from line items
        product_sales: Dict[str, Dict[str, Any]] = {}
        for order in orders:
            for item in order.line_items:
                if item.product_id not in product_sales:
                    product_sales[item.product_id] = {
                        "product_id": item.product_id,
                        "title": item.title,
                        "units_sold": 0,
                        "revenue": 0.0,
                    }
                product_sales[item.product_id]["units_sold"] += item.quantity
                product_sales[item.product_id]["revenue"] += item.price * item.quantity
        
        # Sort by revenue and take top 10
        sorted_products = sorted(
            product_sales.values(),
            key=lambda x: x["revenue"],
            reverse=True
        )[:10]
        
        top_products = [ProductSales.from_dict(p) for p in sorted_products]
        
        return cls(
            total_revenue=total_revenue,
            total_orders=total_orders,
            average_order_value=average_order_value,
            conversion_rate=0.0,  # Requires session data to calculate
            top_products=top_products,
        )
