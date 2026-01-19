from odoo import models, api
import json

class AutomaticEntryWizard(models.TransientModel):
    _inherit = 'account.automatic.entry.wizard'

    def _get_move_dict_vals_change_account(self):
        """ Incluye product_id en TODAS las líneas del traspaso (incluida contrapartida) """
        res = super(AutomaticEntryWizard, self)._get_move_dict_vals_change_account()
        
        # Obtenemos el producto de la primera línea origen que tenga uno asignado
        source_product = self.move_line_ids.filtered(lambda l: l.product_id)[:1].product_id.id
        
        if source_product:
            for move_vals in res:
                for line_tuple in move_vals.get('line_ids', []):
                    line_data = line_tuple[2]
                    # Asignamos el producto a todas las líneas del movimiento de ajuste
                    line_data['product_id'] = source_product
        return res

    def _get_move_dict_vals_change_period(self):
        """ Incluye product_id en TODAS las líneas del cambio de periodo """
        res = super(AutomaticEntryWizard, self)._get_move_dict_vals_change_period()
        
        # En cambio de periodo, Odoo procesa línea por línea.
        # Buscamos el producto correspondiente a la línea original.
        for move_vals in res:
            for line_tuple in move_vals.get('line_ids', []):
                line_data = line_tuple[2]
                
                # Buscamos el producto de la línea origen que generó este movimiento
                # Filtramos por cuenta o nombre para asegurar la relación
                source_line = self.move_line_ids.filtered(
                    lambda l: (l.name == line_data.get('name') or l.account_id.id == line_data.get('account_id')) 
                    and l.product_id
                )[:1]
                
                if source_line:
                    # Asignamos el producto a la línea actual y a su contrapartida 
                    # dentro de este bucle de movimientos generados.
                    line_data['product_id'] = source_line.product_id.id
                else:
                    # Si la línea es la contrapartida pura, buscamos cualquier producto 
                    # disponible en el set de líneas originales del wizard.
                    fallback_product = self.move_line_ids.filtered(lambda l: l.product_id)[:1].product_id.id
                    if fallback_product:
                        line_data['product_id'] = fallback_product
                        
        return res