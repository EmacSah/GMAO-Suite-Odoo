# File: models/maintenance_parts_used_report.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class MaintenancePartsUsedReport(models.AbstractModel):
    _name = 'report.gmao_suite.report_maintenance_parts_used'
    _description = 'Rapport des pièces utilisées en maintenance'

    
    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError("Le formulaire est manquant. Veuillez utiliser l'assistant pour générer le rapport.")

        domain = []
        if data['form'].get('date_from'):
            domain.append(('withdrawal_date', '>=', data['form']['date_from']))
        if data['form'].get('date_to'):
            domain.append(('withdrawal_date', '<=', data['form']['date_to']))
        if data['form'].get('product_ids'):
            domain.append(('product_id', 'in', data['form']['product_ids']))
        if data['form'].get('technician_ids'):
            domain.append(('technician_id', 'in', data['form']['technician_ids']))
        if data['form'].get('state'):
            domain.append(('state', '=', data['form']['state']))

        docs = self.env['maintenance.parts.used'].search(domain)

        return {
            'doc_ids': data.get('ids', docs.ids),
            'doc_model': 'maintenance.parts.used',
            'docs': docs,
            'filters': data['form'],
            'groupby': data['form'].get('groupby'),
            'get_statistics': self._get_statistics,
            'get_replenishment_forecast': self._get_replenishment_forecast,
            'get_top_used_parts': self._get_top_used_parts,
            'get_usage_by_state': self._get_usage_by_state,
            'get_technician_efficiency': self._get_technician_efficiency,
            'get_stock_status_color': self._get_stock_status_color,
            'get_cost_status_color': self._get_cost_status_color,
            'get_usage_status_color': self._get_usage_status_color,
            'get_graphs': self._get_graphs,
        }
    

    def _get_statistics(self, docs):
        total_cost = sum(docs.mapped('real_cost'))
        avg_quantity = sum(docs.mapped('quantity')) / len(docs) if docs else 0
        total_interventions = len(set(docs.mapped('intervention_id')))
        stock_rotation = sum(docs.mapped('quantity')) / sum(docs.mapped('product_id.qty_available')) if sum(docs.mapped('product_id.qty_available')) else 0
        
        return {
            'total_cost': total_cost,
            'avg_quantity': avg_quantity,
            'total_interventions': total_interventions,
            'stock_rotation': stock_rotation,
        }

    def _get_replenishment_forecast(self, docs):
        forecast = []
        for product in docs.mapped('product_id'):
            product_usage = docs.filtered(lambda d: d.product_id == product)
            avg_usage = sum(product_usage.mapped('quantity')) / len(product_usage) if product_usage else 0
            days_to_stockout = (product.qty_available - product.min_stock) / avg_usage if avg_usage else float('inf')
            
            forecast.append({
                'product': product.name,
                'current_stock': product.qty_available,
                'min_stock': product.min_stock,
                'avg_usage': avg_usage,
                'days_to_stockout': days_to_stockout,
                'recommended_order': max(0, product.min_stock - product.qty_available + (avg_usage * 30))  # 30 jours de stock
            })
        
        return forecast

    def _get_top_used_parts(self, docs):
        usage_data = {}
        for doc in docs:
            if doc.product_id in usage_data:
                usage_data[doc.product_id]['quantity'] += doc.quantity
                usage_data[doc.product_id]['cost'] += doc.real_cost
            else:
                usage_data[doc.product_id] = {'quantity': doc.quantity, 'cost': doc.real_cost}
        
        sorted_by_quantity = sorted(usage_data.items(), key=lambda x: x[1]['quantity'], reverse=True)[:5]
        sorted_by_cost = sorted(usage_data.items(), key=lambda x: x[1]['cost'], reverse=True)[:5]
        
        return {
            'by_quantity': sorted_by_quantity,
            'by_cost': sorted_by_cost
        }

    def _get_usage_by_state(self, docs):
        return {state: len(docs.filtered(lambda d: d.state == state)) for state in set(docs.mapped('state'))}

    def _get_technician_efficiency(self, docs):
        efficiency = {}
        for technician in docs.mapped('technician_id'):
            technician_docs = docs.filtered(lambda d: d.technician_id == technician)
            interventions = len(set(technician_docs.mapped('intervention_id')))
            parts_used = sum(technician_docs.mapped('quantity'))
            efficiency[technician.name] = parts_used / interventions if interventions else 0
        
        return efficiency

    def _get_stock_status_color(self, current_stock, min_stock):
        if current_stock <= min_stock:
            return 'red'
        elif current_stock <= min_stock * 1.2:
            return 'orange'
        else:
            return 'green'

    def _get_cost_status_color(self, cost, avg_cost):
        if cost > avg_cost:
            return 'red'
        else:
            return 'green'

    def _get_usage_status_color(self, usage, avg_usage):
        if usage > avg_usage * 1.5:
            return 'blue'
        elif usage < avg_usage * 0.5:
            return 'lightblue'
        else:
            return 'grey'

    def _get_graphs(self, docs):
        graphs = {}
        
        # Graphique en barres des quantités utilisées
        plt.figure(figsize=(10, 6))
        products = docs.mapped('product_id.name')
        quantities = docs.mapped('quantity')
        plt.bar(products, quantities)
        plt.title('Quantités de pièces utilisées')
        plt.xlabel('Produits')
        plt.ylabel('Quantité')
        plt.xticks(rotation=45, ha='right')
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        graphs['quantities_used'] = base64.b64encode(img.getvalue()).decode('ascii')
        plt.close()

        # Diagramme en camembert pour la répartition des coûts
        plt.figure(figsize=(8, 8))
        costs = docs.mapped('real_cost')
        plt.pie(costs, labels=products, autopct='%1.1f%%')
        plt.title('Répartition des coûts par pièce')
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        graphs['cost_distribution'] = base64.b64encode(img.getvalue()).decode('ascii')
        plt.close()

        # Graphique en ligne de l'évolution de l'utilisation
        plt.figure(figsize=(10, 6))
        dates = sorted(set(docs.mapped('withdrawal_date')))
        usage_over_time = {date: sum(d.quantity for d in docs if d.withdrawal_date == date) for date in dates}
        plt.plot(dates, list(usage_over_time.values()))
        plt.title('Évolution de l\'utilisation des pièces')
        plt.xlabel('Date')
        plt.ylabel('Quantité utilisée')
        plt.xticks(rotation=45, ha='right')
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        graphs['usage_evolution'] = base64.b64encode(img.getvalue()).decode('ascii')
        plt.close()

        return graphs