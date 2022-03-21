# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettingsBinauralNomina(models.TransientModel):
	_inherit = 'res.config.settings'

    porcentaje_deduccion_faov = fields.Float(string="Porcentaje de deduccion", help="Porcentaje que se usara para la deduccion", digits=(5,2))

    def set_values(self):
        super(ResConfigSettingsBinauralNomina, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('porcentaje_deduccion_faov',self.porcentaje_deduccion_faov)

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsBinauralNomina, self).get_values()
        res['porcentaje_deduccion_faov'] = self.env['ir.config_parameter'].sudo().get_param('porcentaje_deduccion_faov')
        