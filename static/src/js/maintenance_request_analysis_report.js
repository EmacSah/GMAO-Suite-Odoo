odoo.define('gmao_suite.maintenance_request_analysis_report', function (require) {
    'use strict';

    var core = require('web.core');
    var QWeb = core.qweb;

    function generateCharts(data) {
        // Graphique 1: Évolution du nombre d'interventions
        new Chart(document.getElementById('interventionsEvolutionChart').getContext('2d'), {
            type: 'line',
            data: data.interventions_evolution,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Graphique 2: Temps d'intervention
        new Chart(document.getElementById('interventionTimeChart').getContext('2d'), {
            type: 'bar',
            data: data.intervention_time,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Graphique 3: Temps moyen d'intervention par équipe/priorité
        var pivotData = data.avg_time_by_team_priority;
        var teams = [...new Set(pivotData.map(item => item.team_id[1]))];
        var priorities = ['0', '1', '2', '3'];
        var datasets = priorities.map(priority => ({
            label: 'Priorité ' + priority,
            data: teams.map(team => {
                var item = pivotData.find(i => i.team_id[1] === team && i.priority === priority);
                return item ? item['duration:avg'] : 0;
            }),
            backgroundColor: getColorForPriority(priority)
        }));

        new Chart(document.getElementById('avgTimeByTeamPriorityChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: teams,
                datasets: datasets
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Graphique 4: Répartition des coûts
        new Chart(document.getElementById('costDistributionChart').getContext('2d'), {
            type: 'pie',
            data: data.cost_distribution,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    title: {
                        display: false
                    }
                }
            }
        });
    }

    function getColorForPriority(priority) {
        var colors = {
            '0': 'rgba(255, 99, 132, 0.6)',
            '1': 'rgba(54, 162, 235, 0.6)',
            '2': 'rgba(255, 206, 86, 0.6)',
            '3': 'rgba(75, 192, 192, 0.6)'
        };
        return colors[priority] || 'rgba(0, 0, 0, 0.6)';
    }

    function initReport() {
        var reportDataElement = document.getElementById('report_data');
        if (reportDataElement) {
            var reportData = JSON.parse(reportDataElement.textContent);
            generateCharts(reportData);
        } else {
            console.error('Element with id "report_data" not found');
        }
    }

    // Initialisation du rapport
    $(document).ready(function() {
        initReport();
    });

});