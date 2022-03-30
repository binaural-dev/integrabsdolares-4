from odoo import models, fields, http, tools
from datetime import date
import xlsxwriter
from odoo.http import request, Response
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
from odoo.exceptions import MissingError
from io import BytesIO
import base64
import logging
import pandas
from collections import OrderedDict
from datetime import date
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class WizardMaxcamComision(models.TransientModel):
    _name = 'wizard.municipality.retentions.patent.report'

    date_start = fields.Date(
        string='Fecha Inicio', required=True, default=date.today().replace(day=1))
    date_end = fields.Date(string='Fecha fin', required=True, default=date.today(
    ).replace(day=1)+relativedelta(months=1, days=-1))

    def imprimir_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/get_excel_municipality_retentions_report_patent?id=%s' % self.id,
            'target': 'self'
        }

    def _excel_file(self, tabla, nombre):
        data2 = BytesIO()
        workbook = xlsxwriter.Workbook(data2, {'in_memory': True})
        merge_format = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'border': 1,
            'valign': 'vcenter',
            'fg_color': '#D3D3D3',
            'text_wrap': 1,
            'valign': 'top'
        })
        bold = workbook.add_format({'bold': 1})
        datos = tabla
        worksheet2 = workbook.add_worksheet(nombre)
        worksheet2.set_column('A:Z', 20)
        worksheet2.set_row(0, 23, merge_format)
        worksheet2.set_row(0, 23, merge_format)
        columnas = list(datos.columns.values)
        columns2 = [{'header': r} for r in columnas]
        currency_symbol = self.env.ref('base.VEF').symbol
        money_format = workbook.add_format(
            {'num_format': '#,##0.00 "'+currency_symbol+'"'})
        # control_format = workbook.add_format({'align': 'center'})
        porcent_format = workbook.add_format({'num_format': '0.0 %'})

        data = datos.values.tolist()
        col3 = len(columns2)-1
        col2 = len(data)+1
        cells = xlsxwriter.utility.xl_range(0, 0, col2, col3)

        worksheet2.hide_gridlines(2)
        worksheet2.add_table(
            cells, {'data': data, 'total_row': True, 'columns': columns2, 'autofilter': False})
        workbook.close()
        data2 = data2.getvalue()
        return data2

    def _get_excel_municipality_retention_report(self):

        retentions = self.env['account.municipality.retentions'].search(
            [('date_accounting', '>=', self.date_start), ('date_accounting', '<=', self.date_end), ('state', '=', 'emitted'), ('type', '=', "out_invoice")], order='date_accounting asc')

        lista = []
        cols = OrderedDict([
            ('RUBROS', '12312321'),
            ('CIU', ''),
            ('PRORRATA DEDUCCIONES', ''),
            ('VENTAS BRUTAS (Factura + ND)', ''),
            ('DEVOLUC. VENTAS (NC)', ''),
            ('DSTOS. VENTAS (NC Financiera)', ''),
            ('NOTAS DE DEBITO (ND financiera)', ''),
            ('INGRESOS 100%', ''),
            ('INGRESOS 90%', ''),
            ('INGRESOS 10%', 0.00),
            ('Alic %', ''),
            ('IMPUESTO', 0.00),
            ('MINIMO TRIBUTABLE', 0.00),
            ('ANTICIPO PERIODO', 0.00),
            ('IMPUESTO RESTANTE 10%', 0.00),
            ('ANTICIPO 90%', 0.00),
        ])
        currency = self.env.company.currency_id.name
        numero = 1
        for retention in retentions:
            for retention_line in retention.retention_line_ids:
                rows = OrderedDict()
                rows.update(cols)
                lista.append(rows)
                numero += 1
        tabla = pandas.DataFrame(lista)
        return tabla.fillna(0)


class ControllerMunicipalityRetentionXlsx(http.Controller):

    @ http.route('/web/get_excel_municipality_retentions_report_patent', type='http', auth="user")
    @ serialize_exception
    def download_document(self, id):
        filecontent = ''
        if not id:
            return request.not_found()

        report_obj = request.env['wizard.municipality.retentions.patent.report'].browse(
            int(id))

        tabla = report_obj._get_excel_municipality_retention_report()

        name_document = f"Patente Impuesto Municipal {report_obj.date_start.strftime('%d-%m-%Y')} al {report_obj.date_end.strftime('%d-%m-%Y')}"

        filecontent = report_obj._excel_file(
            tabla, name_document)

        if not filecontent:
            return Response("No hay datos para mostrar", content_type='text/html;charset=utf-8', status=500)
        return request.make_response(filecontent,
                                     [('Content-Type', 'application/pdf'), ('Content-Length', len(filecontent)),
                                      ('Content-Disposition', content_disposition(name_document+'.xlsx'))])


def current_date_format(date):
    months = ("Enero", "Febrero", "Marzo", "Abri", "Mayo", "Junio", "Julio",
              "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    month = months[date.month - 1]
    year = date.year
    message = "{} {}".format(month, year)
    return message
