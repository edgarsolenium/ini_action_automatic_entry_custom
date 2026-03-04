from odoo import models, api
import json

class AutomaticEntryWizard(models.TransientModel):
    _inherit = 'account.automatic.entry.wizard'

    def _get_move_dict_vals_change_account(self):
        """ Sobreescribimos para incluir product_id en el traspaso de cuenta """
        # Llamamos al original para obtener la estructura base
        res = super(AutomaticEntryWizard, self)._get_move_dict_vals_change_account()
        
        # En este método, res[0]['line_ids'] contiene las líneas nuevas
        # Como Odoo agrupa por partner/cuenta/moneda, buscamos el producto
        # de las líneas originales para asignarlo a las nuevas líneas.
        for move_vals in res:
            for line_tuple in move_vals.get('line_ids', []):
                line_data = line_tuple[2]
                # Buscamos en la selección original una línea que coincida con la cuenta
                source_line = self.move_line_ids.filtered(
                    lambda l: 
                        l.account_id.id == line_data.get('account_id')
                        and l.product_id
                        and l.partner_id.id == line_data.get('partner_id')
                        and l.amount_currency == line_data.get('amount_currency')
                )[:1]
                if source_line:
                    line_data['product_id'] = source_line.product_id.id
        return res

    def _get_move_dict_vals_change_period(self):
        """ Sobreescribimos para incluir product_id en el cambio de periodo """
        # Obtenemos los valores generados por el estándar
        res = super(AutomaticEntryWizard, self)._get_move_dict_vals_change_period()
        
        # Odoo genera múltiples movimientos en una lista. 
        # Debemos recorrer cada movimiento y cada línea.
        for move_vals in res:
            for line_tuple in move_vals.get('line_ids', []):
                line_data = line_tuple[2]
                
                # Intentamos encontrar el producto basado en la descripción o cuenta
                # ya que en cambio de periodo la relación es 1 a 1 por línea.
                source_line = self.move_line_ids.filtered(
                    lambda l: (l.name == line_data.get('name') or l.account_id.id == line_data.get('account_id')) 
                    and l.product_id
                )[:1]
                
                if source_line:
                    line_data['product_id'] = source_line.product_id.id
        return res