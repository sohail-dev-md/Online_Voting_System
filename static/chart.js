google.charts.load('current', {'packages':['corechart', 'controls', 'table']});
google.charts.setOnLoadCallback(drawChart);
google.charts.setOnLoadCallback(drawtable);
google.charts.setOnLoadCallback(drawBarChart);


function getRandomint(max) {
  return Math.floor(Math.random() * max);
}

document.addEventListener("DOMContentLoaded", function() {
document.getElementById("toggleButton").addEventListener("click", function() {
    let div1 = document.getElementById("piechart_3d");
    let div2 = document.getElementById("chart_div");

    if (div1.classList.contains("hidden")) {
        // If div1 is hidden, show it and hide div2
        div1.classList.remove("hidden");
        div2.classList.add("hidden");
    } else {
        // If div1 is visible, hide it and show div2
        div1.classList.add("hidden");
        div2.classList.remove("hidden");
    }
});
});

var Rcolor =  [
            ["#ea5545", "#f46a9b", "#ef9b20", "#edbf33", "#ede15b", "#bdcf32", "#87bc45", "#27aeef", "#b33dc6"],
            ["#e60049", "#0bb4ff", "#50e991", "#e6d800", "#9b19f5", "#ffa300", "#dc0ab4", "#b3d4ff", "#00bfa0"],
            ["#b30000", "#7c1158", "#4421af", "#1a53ff", "#0d88e6", "#00b7c7", "#5ad45a", "#8be04e", "#ebdc78"],
            ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"]
];

var rows = [
  ['Elisa', 7],
  ['Robert', 3],
  ['Michael' , 5],
  ['John', 2],
  ['Jessica', 6],
  ['Aaron', 1],
  ['Margareth', 8]
];


rows.sort((a, b) => b[1] - a[1]);
function drawtable() {
var data = new google.visualization.DataTable();
data.addColumn('number', '*');
data.addColumn('string', 'Name');
data.addColumn('number', 'No. of votes');

for (var i = 0; i < rows.length; i++) {
    data.addRow([i + 1, rows[i][0], rows[i][1]]);
}

var table = new google.visualization.Table(document.getElementById('table_div'));

var tableOptions = {
    width: '350px',
    allowHtml: true,
    cssClassNames: {
        headerRow: 'white-text',
        tableRow: 'white-text',
        oddTableRow: 'white-text',
        selectedTableRow: 'white-text'
    }
};

table.draw(data, tableOptions);
}

function drawChart() {
var data = new google.visualization.arrayToDataTable([
    ['Name', 'Votes'],
    ...rows
]);

var options = {
  title: 'Votes Distribution',
  is3D: true,
  width: 350,
  backgroundColor: 'transparent', // Fully transparent background
  chartArea: {
    left: '10%',
    top: 40,
    width: '80%',
    height: '80%',
    backgroundColor: 'transparent'
  },
  titleTextStyle: { color: 'white' },
  legend: { textStyle: { color: 'white' } },
  pieSliceTextStyle: { color: 'black' }
};

var chart = new google.visualization.PieChart(document.getElementById('piechart_3d'));
chart.draw(data, options);
}

function drawBarChart() {
var data = google.visualization.arrayToDataTable([
    ["Element", "Density", { role: "style" }, { role: "annotation", type: "string" }],
    ...rows.map(row => [...row, Rcolor[getRandomint(Rcolor.length)][getRandomint(Rcolor[0].length)], row[1].toString()])
]);

var options = {
    title: "Density of Precious Metals, in g/cm³",
    width: 350,
    backgroundColor: 'transparent',
    bar: { groupWidth: "50%" },
    legend: { position: "none" },
    titleTextStyle: { color: 'white' },
    pieSliceTextStyle: { color: 'white' },
    hAxis: {
        textStyle: { color: '#fff' },
        gridlines: { color: 'transparent' },
        baselineColor: 'black'
    },
    vAxis: {
        gridlines: { color: '#fff', minSpacing: 10 },
        minorGridlines: { color: 'transparent' },
        textStyle: { color: 'white' },
        baselineColor: 'red'
    }
};

var chart = new google.visualization.ColumnChart(document.getElementById("chart_div"));
chart.draw(data, options);
}

window.addEventListener('resize', function() {
drawChart();
drawtable();
drawBarChart();
});
