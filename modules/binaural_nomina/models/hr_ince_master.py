# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class binaural_ince_master(models.Model):
    _name = 'hr.ince.master'
    _description = 'Maestro para datos basicos de INCE Vzla'

    porcentaje_deduccion = fields.Float(string="Porcentaje de deduccion", help="Porcentaje que se usara para la deduccion", digits=(5,2))        
        