import json
import requests
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters
from rest_framework import status
import string
import random

from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet


from app.pagination import PaginationHandlerMixin
from app.serializers import TokenSerializer, MemoSerializer, UserSerializer, ImageSerializer
from app.models import User, Memo, Tag, Image
from app.storages import get_s3_connection

from server.settings.base import env


class BasicPagination(PageNumberPagination):
    page_size_query_param = 'limit'


def get_random_hash(length):
    string_pool = string.ascii_letters + string.digits
    result = ""
    for i in range(length):
        result += random.choice(string_pool)
    return result


# /hello
class HelloView(APIView):
    def get(self, request):
        return Response("GET Hello", status=200)

    def post(self, request):
        return Response("POST Hello", status=200)

    def patch(self, request):
        return Response("PATCH Hello", status=200)

    def delete(self, request):
        return Response("DELETE Hello", status=200)


# /users
class UserView(APIView):
    def get(self, request):
        if request.user.is_anonymous:
            return Response("알 수 없는 유저입니다.", status=404)

        serializer = UserSerializer(request.user)
        return JsonResponse(serializer.data, status=200)

    # for debug
    def post(self, request):
        data = JSONParser().parse(request)
        user_data = {
            "kakao_id": data.get('kakao_id', None),
            "kakao_email": data.get('kakao_email', None),
            "nickname": data.get('nickname', None)
        }
        serializer = TokenSerializer(data=user_data)
        if serializer.is_valid():
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)


# /auth/kakao
class KakaoLoginView(APIView):
    # 카카오 회원가입+로그인
    def post(self, request):
        data = JSONParser().parse(request)
        kakao_access_token = data.get('kakao_access_token', None)
        kakao_auth_url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {kakao_access_token}",
            "Content-type": "application/x-www-form-urlencoded; charset=utf-8"
        }
        kakao_response = requests.post(kakao_auth_url, headers=headers)
        kakao_response = json.loads(kakao_response.text)

        kakao_id = str(kakao_response.get('id', None))
        kakao_account = kakao_response.get('kakao_account', None)
        kakao_email = kakao_account.get('email', None)
        nickname = kakao_account.get('profile', None).get('nickname', None)

        user_data = {
            "kakao_id": kakao_id,
            "kakao_email": kakao_email,
            "nickname": nickname,
        }

        serializer = TokenSerializer(data=user_data)
        if serializer.is_valid():
            return Response(serializer.data, status=200)
        else:
            print(serializer.errors)
        return Response("Kakao Login False", status=400)


# /images
class ImagesView(APIView):
    def post(self, request):
        if request.user.is_anonymous:
            return Response("알 수 없는 유저입니다.", status=404)
        user_kakao_id = request.user.kakao_id
        image = request.FILES['image']
        splited_name = image.name.split('.')
        extension = "." + splited_name[len(splited_name)-1]
        memo_id = request.data['memo_id']

        hash_value = get_random_hash(length=30)
        resource_url = user_kakao_id + "/" + hash_value + extension
        file_name = hash_value + extension
        image_data = {
            "memo": memo_id,
            "url": resource_url,
            "name": file_name
        }
        serializer = ImageSerializer(data=image_data)
        if serializer.is_valid():
            serializer.save()
            s3 = get_s3_connection()
            s3.upload_fileobj(
                image,
                env('S3_BUCKET_NAME'),
                resource_url,
                ExtraArgs={
                    "ContentType": image.content_type,
                }
            )
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)


class MemoList(APIView, PaginationHandlerMixin):
    pagination_class = BasicPagination

    def get(self, request, *args, **kwargs):
        memos = Memo.objects.all().order_by('-created_at')
        page = self.paginate_queryset(memos)
        if page is not None:
            serializer = self.get_paginated_response(MemoSerializer(page, many=True).data)
        else:
            serializer = MemoSerializer(memos, many=True)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = request.user
        print(user)
        if request.user.is_anonymous:
            return JsonResponse("알 수 없는 유저입니다.", status=404)
        serializer = MemoSerializer(data=request.data)
        if serializer.is_valid():
            if request.data['is_tag_new']:
                try: #DB에 중복값이 있다면 저장안함
                    tag = Tag.objects.get(tag_name=request.data['tag_name'])
                except Tag.DoesNotExist:
                    tag = Tag.objects.create(tag_name=request.data['tag_name'], tag_color=request.data['tag_color'], user=user)
                Memo.objects.create(memo_text=request.data['memo_text'], url=request.data['url'], tag=tag)
                memos = Memo.objects.all().order_by('-created_at')
                page = self.paginate_queryset(memos)
                if page is not None:
                    serializer = self.get_paginated_response(MemoSerializer(page, many=True).data)
                else:
                    serializer = MemoSerializer(memos, many=True)
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            else:
                serializer.save()
                memos = Memo.objects.all().order_by('-created_at')
                page = self.paginate_queryset(memos)
                if page is not None:
                    serializer1 = self.get_paginated_response(MemoSerializer(page, many=True).data)
                else:
                    serializer1 = MemoSerializer(memos, many=True)
                return JsonResponse(serializer1.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemoDetial(APIView):
    def get_memos(self, pk):
        return get_object_or_404(Memo, pk=pk)

    def get(self, request, pk):
        memos = self.get_memos(pk=pk)
        serializer = MemoSerializer(memos)
        return JsonResponse(serializer)

    def put(self, request, pk):
        memos = self.get_memos(pk)
        serializer = MemoSerializer(memos)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, tatus=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):  # 특정 Post 삭제
        memos = self.get_memos(pk)
        memos.delete()
        return JsonResponse("삭제 완료", status=status.HTTP_200_OK)


class MemoText(ModelViewSet):
    queryset = Memo.objects.all()
    serializer_class = MemoSerializer
    pagination_class = PageNumberPagination

    def list(self, request, *args, **kwargs):
        queryset = Memo.objects.filter(memo_text__isnull=False).order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)


class MemoLink(ModelViewSet):#링크모아보기
    queryset = Memo.objects.all()
    serializer_class = MemoSerializer
    pagination_class = PageNumberPagination

    def list(self, request, *args, **kwargs):
        queryset = Memo.objects.filter(url__isnull=False).order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)



