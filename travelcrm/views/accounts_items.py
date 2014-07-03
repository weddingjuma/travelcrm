# -*-coding: utf-8-*-

import logging
import colander

from pyramid.view import view_config

from ..models import DBSession
from ..models.account_item import AccountItem
from ..models.address import Address
from ..lib.qb.accounts_items import AccountsItemsQueryBuilder
from ..lib.utils.common_utils import translate as _

from ..forms.accounts_items import AccountItemSchema


log = logging.getLogger(__name__)


class AccountsItems(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(
        context='..resources.accounts_items.AccountsItems',
        request_method='GET',
        renderer='travelcrm:templates/accounts_items/index.mak',
        permission='view'
    )
    def index(self):
        return {}

    @view_config(
        name='list',
        context='..resources.accounts_items.AccountsItems',
        xhr='True',
        request_method='POST',
        renderer='json',
        permission='view'
    )
    def list(self):
        qb = AccountsItemsQueryBuilder(self.context)
        qb.search_simple(
            self.request.params.get('q'),
        )
        qb.advanced_search(
            **self.request.params.mixed()
        )
        id = self.request.params.get('id')
        if id:
            qb.filter_id(id.split(','))
        qb.sort_query(
            self.request.params.get('sort'),
            self.request.params.get('order', 'asc')
        )
        qb.page_query(
            int(self.request.params.get('rows')),
            int(self.request.params.get('page'))
        )
        return {
            'total': qb.get_count(),
            'rows': qb.get_serialized()
        }

    @view_config(
        name='add',
        context='..resources.accounts_items.AccountsItems',
        request_method='GET',
        renderer='travelcrm:templates/accounts_items/form.mak',
        permission='add'
    )
    def add(self):
        return {'title': _(u'Add Account Item')}

    @view_config(
        name='add',
        context='..resources.accounts_items.AccountsItems',
        request_method='POST',
        renderer='json',
        permission='add'
    )
    def _add(self):
        schema = AccountItemSchema().bind(request=self.request)

        try:
            controls = schema.deserialize(self.request.params)
            account_item = AccountItem(
                name=controls.get('name'),
                item_type=controls.get('item_type'),
                resource=self.context.create_resource()
            )
            DBSession.add(account_item)
            DBSession.flush()
            return {
                'success_message': _(u'Saved'),
                'response': account_item.id
            }
        except colander.Invalid, e:
            return {
                'error_message': _(u'Please, check errors'),
                'errors': e.asdict()
            }

    @view_config(
        name='edit',
        context='..resources.accounts_items.AccountsItems',
        request_method='GET',
        renderer='travelcrm:templates/accounts_items/form.mak',
        permission='edit'
    )
    def edit(self):
        account_item = AccountItem.get(self.request.params.get('id'))
        return {'item': account_item, 'title': _(u'Edit AccountItem')}

    @view_config(
        name='edit',
        context='..resources.accounts_items.AccountsItems',
        request_method='POST',
        renderer='json',
        permission='edit'
    )
    def _edit(self):
        schema = AccountItemSchema().bind(request=self.request)
        account_item = AccountItem.get(self.request.params.get('id'))
        try:
            controls = schema.deserialize(self.request.params)
            account_item.name = controls.get('name')
            account_item.item_type = controls.get('item_type')
            return {
                'success_message': _(u'Saved'),
                'response': account_item.id
            }
        except colander.Invalid, e:
            return {
                'error_message': _(u'Please, check errors'),
                'errors': e.asdict()
            }

    @view_config(
        name='delete',
        context='..resources.accounts_items.AccountsItems',
        request_method='GET',
        renderer='travelcrm:templates/accounts_items/delete.mak',
        permission='delete'
    )
    def delete(self):
        return {
            'title': _(u'Delete Accounts Items'),
            'rid': self.request.params.get('rid')
        }

    @view_config(
        name='delete',
        context='..resources.accounts_items.AccountsItems',
        request_method='POST',
        renderer='json',
        permission='delete'
    )
    def _delete(self):
        errors = 0
        for id in self.request.params.getall('id'):
            item = AccountItem.get(id)
            if item:
                DBSession.begin_nested()
                try:
                    DBSession.delete(item)
                    DBSession.commit()
                except:
                    errors += 1
                    DBSession.rollback()
        if errors > 0:
            return {
                'error_message': _(
                    u'Some objects could not be delete'
                ),
            }
        return {'success_message': _(u'Deleted')}
