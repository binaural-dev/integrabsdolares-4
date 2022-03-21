# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class binaural_paroforzoso_master(models.Model):
    _name = 'hr.paroforzoso.master'
    _description = 'Maestro para datos basicos de paro forzoso Vzla'

    porcentaje_deduccion = fields.Float(string="Porcentaje de deduccion", help="Porcentaje que se usara para la deduccion", digits=(5,2))
    tope_salarios = fields.Integer(string="Tope salario", help="Cantidad de salarios maximos usados para el calculo de la deduccion")
    monto_maximo = fields.Float(string="Monto maximo deduccion", readonly=True, compute="_compute_monto_maximo")

    @api.depends('porcentaje_deduccion', 'tope_salarios')
    def _compute_monto_maximo(self):
        for rec in self:
            rec.monto_maximo = rec.porcentaje_deduccion * rec.monto_maximo
        