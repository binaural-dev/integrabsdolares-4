# -*- coding: utf-8 -*-

import logging
import xlwt
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import xlwt
import io
import base64

_logger = logging.getLogger(__name__)


class MunicipalityRetentions(models.Model):
    _name = 'account.municipality.retentions'
    _description = 'Retenciones Municipales'

    name = fields.Char(string="Número de Comprobante", readonly=True)
    date = fields.Date(string="Fecha de Comprobante")
    type = fields.Selection(selection=[('out_invoice', 'Factura de Cliente'), (
        'in_invoice', 'Factura de Proveedor')], string="Tipo de Comprobante", readonly=True)
    date_accounting = fields.Date(string="Fecha Contable")
    partner_id = fields.Many2one('res.partner', string="Razón Social")
    retention_line_ids = fields.One2many(
        'account.municipality.retentions.line', 'retention_id', string="Retenciones")

    def get_sequence_municipality_retention(self):
        sequence = self.env['ir.sequence'].search(
            [('code', '=', 'retention.municipality.retention.control.number')])
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': 'Numero de control',
                'code': 'retention.municipality.retention.control.number',
                'padding': 5
            })
        return sequence.next_by_code('retention.municipality.retention.control.number')

    def action_validate(self):
        context = dict(self._context or {})
        for retention_line in self.retention_line_ids:
            retention_line._calculate_retention()
            if not'from_invoice' in context:
                retention_line.invoice_id.write({
                    "municipality_tax_voucher_id": self.id,
                    "municipality_tax": True
                })

        journal_id = int(self.env['ir.config_parameter'].get_param(
            'journal_municipal_retention'))
        account_id = int(self.env['ir.config_parameter'].get_param(
            'account_municipal_retention'))

        entries_to_post = []

        if self.type == 'in_invoice':
            for line in self.retention_line_ids:
                to_post = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': self.date_accounting,
                    'journal_id': journal_id,
                    'foreign_currency_rate': line.invoice_id.foreign_currency_rate,
                    'line_ids': [
                        (0, 0, {
                            "account_id": line.invoice_id.line_ids[0].account_id.id,
                            "partner_id": line.invoice_id.partner_id.id,
                            "foreign_currency_rate": line.foreign_rate,
                            "debit": line.total_retained,
                            'currency_id': line.currency_id.id,
                        }),
                        (0, 0, {
                            "account_id": account_id,
                            "partner_id": line.invoice_id.partner_id.id,
                            "foreign_currency_rate": line.foreign_rate,
                            "credit": line.total_retained,
                            'currency_id': line.currency_id.id,
                        })
                    ],
                })
                entries_to_post.append(to_post)

        for index, retention_line in enumerate(self.retention_line_ids):
            entries_to_post[index].action_post()
            retention_line.invoice_id.js_assign_outstanding_line(
                entries_to_post[index].line_ids[0].id)

        sequence = self.get_sequence_municipality_retention()
        self.name = str(sequence)
        
    def action_open_wizard(self):
        return { 
            'name': 'Reporte de Retenciones Municipales',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'wizard.municipality.retentions',
            'context': {'default_retention_id': self.id},
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class MunicipalityRetentionsLine(models.Model):
    _name = "account.municipality.retentions.line"
    _description = 'Retenciones Municipales Linea'

    name = fields.Char(string="Descripción", default="RET-Municipal")
    retention_id = fields.Many2one(
        'account.municipality.retentions', string="Retencion")
    invoice_id = fields.Many2one(
        'account.move', string='Factura', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', default=lambda self: self.env.user.company_id.currency_id)
    total_invoice = fields.Monetary(
        string="Total Facturado", related="invoice_id.amount_total")
    invoice_amount_untaxed = fields.Monetary(
        string="Base Imponible", related="invoice_id.amount_untaxed")
    economic_activity_id = fields.Many2one(
        'economic.activity', string="Actividad Economica")
    activity_aliquot = fields.Float(
        string="Aliquota", related="economic_activity_id.aliquot")
    total_retained = fields.Float(string="Retenido")
    foreign_rate = fields.Float(
        string="tasa foranea", related="invoice_id.foreign_currency_rate")
    foreign_total_invoice = fields.Monetary(
        string="Total Factura Alterno", related="invoice_id.foreign_amount_total")
    foreign_invoice_amount_untaxed = fields.Monetary(
        string="Base Imponible Alterno", related="invoice_id.foreign_amount_untaxed")
    foreign_total_retained = fields.Float(string="Retenido Alterno")
    municipality_id = fields.Many2one(
        'res.country.municipality', string="Municipio", related="economic_activity_id.municipality_id")

    @api.constrains('total_retained', 'total_invoice', 'foreign_total_retained')
    def _constraint_municipality_tax(self):
        for record in self:
            if record.total_retained == 0 or record.total_invoice == 0 or record.foreign_total_retained == 0:
                raise ValidationError(
                    "No se puede crear una retención con valores en cero")

    @api.onchange('invoice_id')
    def default_economic_activity(self):
        if self.invoice_id:
            if not self.invoice_id.partner_id.economic_activity_id:
                raise UserError(
                    "Debe registrar actividad economica del cliente/proveedor")

            self.economic_activity_id = self.invoice_id.partner_id.economic_activity_id

    def get_rate_currency(self, currency_name, rate):
        decimal_function = self.env['decimal.precision'].search(
            [('name', '=', 'decimal_quantity')])
        foreign_currency_name = 'USD' if currency_name == 'VEF' else 'VEF'

        return decimal_function.getCurrencyValue(
            rate, currency_name, foreign_currency_name, 'CALC')

    def _calculate_retention(self):
        self.total_retained = self.invoice_amount_untaxed * \
            (self.activity_aliquot/100)
        self.get_rate_currency(
            self.currency_id.name, self.foreign_rate)
        self.foreign_total_retained = self.get_rate_currency(
            self.currency_id.name, self.foreign_rate) * self.total_retained

    @api.onchange('economic_activity_id')
    def onchange_economic_activity_id(self):
        self._calculate_retention()
