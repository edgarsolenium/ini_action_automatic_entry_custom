from odoo import api, models, fields, _

import json


class AutomaticEntryWizard(models.TransientModel):
    _inherit = 'account.automatic.entry.wizard'

    @api.depends('move_data')
    def _compute_preview_move_data(self):
        super()._compute_preview_move_data()
        for record in self:
            preview = json.loads(record.preview_move_data)
            move_vals = json.loads(record.move_data)

            # Collect all product_ids from move lines and resolve names
            product_ids = set()
            for move in move_vals:
                for (_mode, _id, line) in move.get('line_ids', []):
                    pid = line.get('product_id')
                    if pid:
                        product_ids.add(pid)

            if not product_ids:
                continue

            product_names = {
                p.id: p.display_name
                for p in self.env['product.product'].browse(list(product_ids))
            }

            # Add product column after 'name' (Label)
            columns = preview.get('options', {}).get('columns', [])
            # Find the index after 'name' to insert
            insert_idx = next(
                (i + 1 for i, c in enumerate(columns) if c.get('field') == 'name'),
                len(columns),
            )
            columns.insert(insert_idx, {'field': 'product_id', 'label': _('Product')})

            # Inject product names into preview line data
            for group in preview.get('groups_vals', []):
                for line in group.get('columns_vals', []):
                    pid = line.get('product_id')
                    if isinstance(pid, int) and pid in product_names:
                        line['product_id'] = product_names[pid]
                    elif pid and pid not in product_names:
                        line.setdefault('product_id', '')

            record.preview_move_data = json.dumps(preview)

    def _get_move_dict_vals_change_account(self):
        """Override to avoid grouping lines by partner — create a 1-to-1
        correspondence between original lines and new entry lines, and
        carry over product_id."""
        line_vals = []

        for line in self.move_line_ids.filtered(lambda x: x.account_id != self.destination_account_id):
            counterpart_currency = line.currency_id
            counterpart_amount_currency = line.amount_currency

            if self.destination_account_id.currency_id and self.destination_account_id.currency_id != self.company_id.currency_id:
                counterpart_currency = self.destination_account_id.currency_id
                counterpart_amount_currency = self.company_id.currency_id._convert(
                    line.balance, self.destination_account_id.currency_id, self.company_id, line.date,
                )

            if counterpart_currency.is_zero(counterpart_amount_currency) and self.company_id.currency_id.is_zero(line.balance):
                continue

            source_accounts = self.move_line_ids.mapped('account_id')
            counterpart_label = (
                _("Transfer from %s", source_accounts.display_name)
                if len(source_accounts) == 1
                else _("Transfer counterpart")
            )

            # Counterpart line (destination account)
            counterpart_vals = {
                'name': counterpart_label,
                'debit': self.company_id.currency_id.round(line.balance) if line.balance > 0 else 0,
                'credit': self.company_id.currency_id.round(-line.balance) if line.balance < 0 else 0,
                'account_id': self.destination_account_id.id,
                'partner_id': line.partner_id.id or None,
                'amount_currency': counterpart_currency.round(
                    ((-1 if line.balance < 0 else 1) * abs(counterpart_amount_currency))
                ) or 0,
                'currency_id': counterpart_currency.id,
                'analytic_distribution': line.analytic_distribution,
            }
            if line.product_id:
                counterpart_vals['product_id'] = line.product_id.id
            line_vals.append(counterpart_vals)

            # Source line (original account, reversed)
            source_vals = {
                'name': _('Transfer to %s', self.destination_account_id.display_name or _('[Not set]')),
                'debit': self.company_id.currency_id.round(-line.balance) if line.balance < 0 else 0,
                'credit': self.company_id.currency_id.round(line.balance) if line.balance > 0 else 0,
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id or None,
                'currency_id': line.currency_id.id,
                'amount_currency': (-1 if line.balance > 0 else 1) * abs(line.amount_currency),
                'analytic_distribution': line.analytic_distribution,
            }
            if line.product_id:
                source_vals['product_id'] = line.product_id.id
            line_vals.append(source_vals)

        return [{
            'currency_id': self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id,
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': fields.Date.to_string(self.date),
            'ref': _("Transfer entry to %s", self.destination_account_id.display_name or ''),
            'line_ids': [(0, 0, line) for line in line_vals],
        }]

    def _get_move_line_dict_vals_change_period(self, aml, date):
        """Override to carry over product_id in change period entries."""
        res = super()._get_move_line_dict_vals_change_period(aml, date)
        if aml.product_id:
            for _mode, _id, vals in res:
                vals['product_id'] = aml.product_id.id
        return res
