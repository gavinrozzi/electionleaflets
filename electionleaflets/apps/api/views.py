import datetime

from django.http import HttpResponse
from django.utils.html import escape

from leaflets.models import Leaflet, LeafletImage
from constituencies.models import Constituency
from people.models import Person
from uk_political_parties.models import Party

from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import (ConstituencySerializer, PartySerializer,
                          LeafletMinSerializer, LeafletSerializer, LeafletImageSerializer)


class StandardResultsSetPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 1000


class LeafletPermissions(BasePermission):

    def has_object_permission(self, request, view, obj):
        # Allow unauthenticated users to GET and POST
        # but not PUT, PATCH and DELETE
        if request.method in ['GET', 'POST']:
            return True
        else:
            return request.user == obj.owner


class ReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS


class ConstituencyViewSet(viewsets.ModelViewSet):
    queryset = Constituency.objects.all()
    serializer_class = ConstituencySerializer


class PartyViewSet(viewsets.ModelViewSet):
    queryset = Party.objects.all()
    serializer_class = PartySerializer


class LeafletImageViewSet(viewsets.ModelViewSet):
    queryset = LeafletImage.objects.all()
    serializer_class = LeafletImageSerializer
    pagination_class = StandardResultsSetPagination


class LeafletViewSet(viewsets.ModelViewSet):
    queryset = Leaflet.objects.all()
    serializer_class = LeafletSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (LeafletPermissions, )


class LatestByConstituencyView(APIView):

    permission_classes = (ReadOnly, )

    def get(self, request, format=None):
        all_constituencies = {}
        TIME_SINCE = datetime.datetime.now() - datetime.timedelta(weeks=20)
        LIMIT = 3
        for constituency in Constituency.objects.all():
            leaflets = LeafletSerializer(
                Leaflet.objects.filter(
                    constituency=constituency,
                    date_uploaded__gt=TIME_SINCE,
                )[:LIMIT], many=True).data
            all_constituencies[constituency.pk] = leaflets
        return Response(all_constituencies)


class LatestByPersonView(APIView):

    permission_classes = (ReadOnly, )

    def get(self, request, format=None):
        all_people = {}
        TIME_SINCE = datetime.datetime.now() - datetime.timedelta(weeks=20)
        LIMIT = 3
        for person in Person.objects.exclude(leaflet=None):
            leaflets = LeafletMinSerializer(
                Leaflet.objects.filter(
                    publisher_person=person,
                    date_uploaded__gt=TIME_SINCE,
                )[:LIMIT], many=True, context={'request': request}).data
            all_people[person.remote_id] = leaflets
        return Response(all_people)


class StatsView(APIView):

    permission_classes = (ReadOnly, )

    def get(self, request, format=None):
        stats = {
            'leaflets': {}
        }
        stats['leaflets']['total'] = \
            Leaflet.objects.all().count()

        yesterday = datetime.datetime.now() - datetime.timedelta(hours=24)
        stats['leaflets']['last_24_hours'] = \
            Leaflet.objects.filter(date_uploaded__gt=yesterday).count()

        return Response(stats)


def latest(request, format):
    # TODO: Fix this to work properly
    from leaflets.models import Leaflet

    leaflets = Leaflet.objects.order_by('-id').all()[0:20]
    resp = []
    for leaflet in leaflets:
        d = {}
        if leaflet.constituency_id:
            d['constituency'] = leaflet.constituency.name
        else:
            d['constituency'] = 'Unknown'
        d['constituency'] = str(d['constituency'])
        d['uploaded_date'] = str(leaflet.date_uploaded)
        d['delivery_date'] = str(leaflet.date_delivered)
        d['title'] = escape(leaflet.title)
        d['description'] = escape(leaflet.description)
        if leaflet.publisher_party_id:
            d['party'] = escape(leaflet.publisher_party.party_name)
        else:
            d['party'] = "Unknown"
        i = leaflet.get_first_image()
        d['image'] = i.image.url
        d['link'] = leaflet.get_absolute_url()
        resp.append(d)

    output = '<?xml version="1.0" ?>\n'
    output += "<leaflets>"
    for d in resp:
        output += "<leaflet>"
        for k, v in d.items():
            output += "<" + k + ">"
            output += v
            output += "</" + k + ">"
        output += "</leaflet>"

    output += "</leaflets>"
    return HttpResponse(output, content_type='text/xml')
