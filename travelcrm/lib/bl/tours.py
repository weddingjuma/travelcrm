# -*coding: utf-8-*-

from sqlalchemy import func

from ...models import DBSession
from ...models.resource import Resource
from ...models.tour import Tour
from ...models.person import Person
from ...models.invoice import Invoice
from ...models.service_item import ServiceItem
from ...models.service import Service
from ...models.account_item import AccountItem
from ...models.currency import Currency
from ...models.liability import Liability
from ...models.liability_item import LiabilityItem

from ...lib.bl import (
    InvoiceFactory,
    LiabilityFactory
)
from ...lib.bl.currencies_rates import query_convert_rates
from ...lib.utils.common_utils import money_cast


def calc_base_price(tour):
    assert isinstance(tour, Tour), u"Must be tour instance"
    base_tour_rate = (
        query_convert_rates(tour.currency_id, tour.deal_date)
        .scalar()
    )
    if base_tour_rate is None:
        base_tour_rate = 1
    tour.base_price = money_cast(base_tour_rate * tour.price)

    for service_item in tour.services_items:
        base_service_rate = (
            query_convert_rates(
                service_item.currency_id, tour.deal_date
            )
            .scalar()
        )
        if base_service_rate is None:
            base_service_rate = 1
        service_item.base_price = money_cast(
            base_service_rate * service_item.price
        )
    return tour


class TourInvoiceFactory(InvoiceFactory):

    @classmethod
    def bind_invoice(cls, resource_id, invoice):
        tour = (
            DBSession.query(Tour)
            .filter(Tour.resource_id == resource_id)
            .first()
        )
        tour.invoice = invoice
        return tour

    @classmethod
    def get_invoice(cls, resource_id):
        tour = (
            DBSession.query(Tour)
            .filter(Tour.resource_id == resource_id)
            .first()
        )
        return tour.invoice

    @classmethod
    def get_base_sum(cls, resource_id):
        tour = (
            DBSession.query(Tour)
            .filter(Tour.resource_id == resource_id)
            .first()
        )
        return tour.base_sum

    @classmethod
    def query_list(cls):
        subq_services = (
            DBSession.query(
                Tour.id,
                func.sum(ServiceItem.base_price).label('base_price')
            )
            .join(Tour, ServiceItem.tour)
            .group_by(Tour.id)
            .subquery()
        )
        query = (
            DBSession.query(
                Resource.id.label('resource_id'),
                Person.name.label('customer'),
                (Tour.base_price + func.coalesce(subq_services.c.base_price, 0))
                .label('sum'),
                Invoice.id.label('invoice_id'),
            )
            .join(Resource, Tour.resource)
            .join(Person, Tour.customer)
            .join(Invoice, Tour.invoice)
            .outerjoin(subq_services, subq_services.c.id == Tour.id)
        )
        return query

    @classmethod
    def services_info(cls, resource_id, currency_id=None):
        tour = (
            DBSession.query(Tour)
            .filter(Tour.resource_id == resource_id)
            .first()
        )
        rate = query_convert_rates(currency_id, tour.deal_date).scalar()
        if not rate:
            rate = 1
        query = (
            DBSession.query(
                Service.id.label('id'),
                Service.name.label('name'),
                Tour.base_price.label('base_price')
            )
            .join(Service, Tour.service)
            .filter(Tour.id == tour.id)
        )
        query = query.union_all(
            DBSession.query(
                Service.id.label('id'),
                Service.name.label('name'),
                ServiceItem.base_price.label('base_price')
            )
            .join(Tour, ServiceItem.tour)
            .join(Service, ServiceItem.service)
            .filter(Tour.id == tour.id)
        )
        subq = query.subquery()
        return (
            DBSession.query(
                subq.c.name,
                func.count(subq.c.id).label('cnt'),
                money_cast(subq.c.base_price / rate).label('unit_price'),
                money_cast(func.sum(subq.c.base_price) / rate).label('price')
            )
            .group_by(subq.c.id, subq.c.name, subq.c.base_price)
            .order_by(subq.c.name)
        )

    @classmethod
    def accounts_items_info(cls, resource_id, currency_id=None):
        tour = (
            DBSession.query(Tour)
            .filter(Tour.resource_id == resource_id)
            .first()
        )
        rate = query_convert_rates(currency_id, tour.deal_date).scalar()
        if not rate:
            rate = 1
        query = (
            DBSession.query(
                AccountItem.id.label('id'),
                AccountItem.name.label('name'),
                Tour.base_price.label('base_price')
            )
            .join(Service, Tour.service)
            .join(AccountItem, Service.account_item)
            .filter(Tour.id == tour.id)
        )
        query = query.union_all(
            DBSession.query(
                AccountItem.id.label('id'),
                AccountItem.name.label('name'),
                ServiceItem.base_price.label('base_price')
            )
            .join(Tour, ServiceItem.tour)
            .join(Service, ServiceItem.service)
            .join(AccountItem, Service.account_item)
            .filter(Tour.id == tour.id)
        )
        subq = query.subquery()
        return (
            DBSession.query(
                subq.c.id,
                subq.c.name,
                func.count(subq.c.id).label('cnt'),
                money_cast(func.sum(subq.c.base_price) / rate).label('price')
            )
            .group_by(subq.c.id, subq.c.name)
            .order_by(subq.c.name)
        )


class TourLiabilityFactory(LiabilityFactory):

    @classmethod
    def _get_resource(cls, resource_id):
        return (
            DBSession.query(Tour)
            .filter(Tour.resource_id == resource_id)
            .first()
        )

    @classmethod
    def query_list(cls):
        subq_services = (
            DBSession.query(
                Tour.id,
                func.sum(ServiceItem.base_price).label('base_price')
            )
            .join(Tour, ServiceItem.tour)
            .group_by(Tour.id)
            .subquery()
        )
        subq_liability = (
            DBSession.query(
                Liability.id,
                money_cast(
                    func.coalesce(
                        func.sum(LiabilityItem.base_price), 0
                    )
                ).label('base_price')
            )
            .join(LiabilityItem, Liability.liabilities_items)
            .group_by(Liability.id)
            .subquery()
        )
        resource_sum_stmt = money_cast(
            Tour.base_price + func.coalesce(
                subq_services.c.base_price, 0
            )
        )
        query = (
            DBSession.query(
                Resource.id.label('resource_id'),
                resource_sum_stmt.label('resource_sum'),
                (resource_sum_stmt - subq_liability.c.base_price).label(
                    'profit'
                ),
                subq_liability.c.base_price.label('base_price'),
                Liability.id.label('liability_id'),
            )
            .join(Resource, Tour.resource)
            .join(Liability, Tour.liability)
            .join(subq_liability, subq_liability.c.id == Liability.id)
            .outerjoin(subq_services, subq_services.c.id == Tour.id)
        )
        return query

    @classmethod
    def bind_liability(cls, resource_id, liability):
        tour = cls._get_resource(resource_id)
        tour.liability = liability
        return tour

    @classmethod
    def get_source_date(cls, resource_id):
        tour = cls._get_resource(resource_id)
        return tour.deal_date

    @classmethod
    def get_liability(cls, resource_id):
        tour = cls._get_resource(resource_id)
        return tour.liability

    @classmethod
    def services_info(cls, resource_id):
        tour = cls._get_resource(resource_id)
        query = (
            DBSession.query(
                Service.id.label('id'),
                Service.name.label('name'),
                Tour.price.label('price'),
                Currency.iso_code.label('currency'),
                Currency.id.label('currency_id'),
                Tour.touroperator_id.label('touroperator_id'),
            )
            .join(Service, Tour.service)
            .join(Currency, Tour.currency)
            .filter(Tour.id == tour.id)
        )
        query = query.union_all(
            DBSession.query(
                Service.id.label('id'),
                Service.name.label('name'),
                ServiceItem.price.label('price'),
                Currency.iso_code.label('currency'),
                Currency.id.label('currency_id'),
                ServiceItem.touroperator_id.label('touroperator_id'),
            )
            .join(Tour, ServiceItem.tour)
            .join(Service, ServiceItem.service)
            .join(Currency, ServiceItem.currency)
            .filter(Tour.id == tour.id)
        )
        subq = query.subquery()
        return (
            DBSession.query(
                subq.c.id,
                subq.c.name,
                func.sum(subq.c.price).label('price'),
                subq.c.currency,
                subq.c.currency_id,
                subq.c.touroperator_id,
            )
            .group_by(
                subq.c.id,
                subq.c.name,
                subq.c.currency_id,
                subq.c.currency,
                subq.c.touroperator_id
            )
            .order_by(subq.c.name)
        )