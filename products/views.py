import math
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from adminpanel.permissions import IsAdminRole
from .models import Product, ProductLike
from .serializers import ProductSerializer, AdminProductSerializer, ProductFilterSerializer
from .services import ProductService


class ProductListView(APIView):
    """GET /api/products/ — public. POST /api/products/ — admin only."""

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [AllowAny()]

    def get(self, request):
        filter_serializer = ProductFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response({'success': False, 'errors': filter_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        products, total = ProductService.get_filtered_list(filter_serializer.validated_data)
        limit = filter_serializer.validated_data['limit']
        page  = filter_serializer.validated_data['page']

        return Response({
            'success':  True,
            'total':    total,
            'page':     page,
            'pages':    math.ceil(total / limit),
            'products': ProductSerializer(products, many=True).data,
        })

    def post(self, request):
        serializer = AdminProductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        return Response({'success': True, 'product': AdminProductSerializer(product).data},
                        status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    """GET /api/products/<id>/ — public. PUT/DELETE — admin only."""

    def get_permissions(self):
        if self.request.method in ('PUT', 'DELETE'):
            return [IsAdminRole()]
        return [AllowAny()]

    def get(self, request, product_id):
        try:
            product = ProductService.get_by_id(product_id)
        except Product.DoesNotExist:
            return Response({'success': False, 'message': 'Product not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'product': ProductSerializer(product).data})

    def put(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'success': False, 'message': 'Product not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = AdminProductSerializer(product, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({'success': True, 'product': serializer.data})

    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'success': False, 'message': 'Product not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        product.is_active = False
        product.save()
        return Response({'success': True, 'message': 'Product removed.'})


class ProductLikeView(APIView):
    """GET /api/products/<id>/like/ — check; POST — toggle like."""
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        liked = ProductLike.objects.filter(user=request.user, product_id=product_id).exists()
        return Response({'success': True, 'liked': liked})

    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'success': False, 'message': 'Product not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
        if not created:
            like.delete()
            return Response({'success': True, 'liked': False})
        return Response({'success': True, 'liked': True}, status=status.HTTP_201_CREATED)


class LikedProductsView(APIView):
    """GET /api/products/liked/ — returns all products the current user has liked."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        likes    = ProductLike.objects.filter(user=request.user).select_related('product')
        products = [like.product for like in likes]
        return Response({'success': True, 'products': ProductSerializer(products, many=True).data})
