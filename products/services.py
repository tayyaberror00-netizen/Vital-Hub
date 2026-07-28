from django.db.models import Q
from .models import Product


# --- Strategy pattern: sorting strategies ---
SORT_STRATEGIES = {
    'price_asc':  'price',
    'price_desc': '-price',
    'newest':     '-created_at',
}


class ProductService:
    """
    PRESENTER (Service) layer — all product business logic.
    Implements Strategy pattern for sorting, Repository pattern via ORM.
    """

    @staticmethod
    def get_filtered_list(filters: dict) -> tuple[list, int]:
        """
        Return (queryset_page, total_count) applying category, search,
        sort strategy, and pagination.
        """
        qs = Product.objects.filter(is_active=True)

        # Filter by category
        if filters.get('category'):
            qs = qs.filter(category=filters['category'])

        # Full-text search across name and description
        if filters.get('search'):
            term = filters['search']
            qs = qs.filter(Q(name__icontains=term) | Q(description__icontains=term))

        # Price range
        if filters.get('min_price') is not None:
            qs = qs.filter(price__gte=filters['min_price'])
        if filters.get('max_price') is not None:
            qs = qs.filter(price__lte=filters['max_price'])

        # AR / 3D model filter — only filter when the string 'true' is explicitly sent
        if filters.get('has_model') == 'true':
            qs = qs.filter(has_model=True)

        # Apply sort strategy
        order_field = SORT_STRATEGIES.get(filters.get('sort', 'newest'), '-created_at')
        qs = qs.order_by(order_field)

        total = qs.count()

        # Pagination
        page  = int(filters.get('page', 1))
        limit = int(filters.get('limit', 20))
        start = (page - 1) * limit
        return list(qs[start:start + limit]), total

    @staticmethod
    def get_by_id(product_id: str) -> Product:
        """Fetch a single active product or raise DoesNotExist."""
        return Product.objects.get(id=product_id, is_active=True)

    @staticmethod
    def deduct_stock(product: Product, quantity: int) -> None:
        """Atomically reduce stock — raises ValueError if insufficient."""
        if product.stock < quantity:
            raise ValueError(f'Insufficient stock for "{product.name}".')
        Product.objects.filter(id=product.id).update(stock=product.stock - quantity)
