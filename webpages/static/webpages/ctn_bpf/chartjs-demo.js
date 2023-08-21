/*
 Template Name: Xeloro - Admin & Dashboard Template
 Author: Myra Studio
 File: Chart Js
*/

/*
!function(e){"use strict";
e(function(){if(e("#pieChart").length){var a=e("#pieChart").get(0).getContext("2d");
new Chart(a,{type:"pie",data:{datasets:[{data:[21,16,48,31],backgroundColor:["#3F51B5","#f8ac5a","#00c2b2","#f15050"],borderColor:["#3F51B5","#f8ac5a","#00c2b2","#f15050"]}],labels:["Samsung","Apple","Vivo","Motorola"]},options:{responsive:!0,animation:{animateScale:!0,animateRotate:!0}}})}

/*if(e("#lineChart").length){
var r=e("#lineChart").get(0).getContext("2d");

var linechart= new Chart(r,{type:"line",
data:{labels:[],
datasets:[
{label:"Apple",data:[],borderColor:["#1d84c6"],
borderWidth:3,fill:!1,pointBackgroundColor:"#ffffff",pointBorderColor:"#1d84c6"},

{label:"Samsung",data:[],borderColor:["#00c2b2"],
borderWidth:3,fill:!1,pointBackgroundColor:"#ffffff",pointBorderColor:"#00c2b2"}]},

options:{scales:{yAxes:[{gridLines:{drawBorder:!1,borderDash:[3,3]},ticks:{min:0}}],
xAxes:[{gridLines:{display:!1,drawBorder:!1,color:"#ffffff"}}]},elements:{line:{tension:.2},
point:{radius:4}},stepsize:1}}
)};

if(e("#areaChart").length){var o=e("#areaChart").get(0).getContext("2d");new Chart(o,{type:"line",data:{labels:["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],datasets:[{data:[22,23,28,20,27,20,20,24,10,35,20,25],backgroundColor:["#23b5e2"],borderColor:["#23b5e2"],borderWidth:1,fill:"origin",label:"purchases"},{data:[50,40,48,70,50,63,63,42,42,51,35,35],backgroundColor:["#7266bb"],borderColor:["#7266bb"],borderWidth:1,fill:"origin",label:"services"},{data:[95,75,90,105,95,95,95,100,75,95,90,105],backgroundColor:["#dfe3e9"],borderColor:["#dfe3e9"],borderWidth:1,fill:"origin",label:"services"}]},options:{responsive:!0,maintainAspectRatio:!0,plugins:{filler:{propagate:!1}},scales:{xAxes:[{gridLines:{display:!1,drawBorder:!1,color:"transparent",zeroLineColor:"#eeeeee"}}],yAxes:[{gridLines:{drawBorder:!1,borderDash:[3,3]}}]},legend:{display:!1},tooltips:{enabled:!0},elements:{line:{tension:0},point:{radius:0}}}})}if(
areaChart,e("#barChart").length){var t=e("#barChart").get(0).getContext("2d");
new Chart(t,{type:"bar",data:{labels:[],datasets:[{label:"Apple",data:[],backgroundColor:"#2ac14e"},
{label:"Samsung",data:[],backgroundColor:"#f8ac5a"}]},
options:{responsive:!0,maintainAspectRatio:!0,scales:{yAxes:[{display:!1,gridLines:{drawBorder:!1},ticks:{fontColor:"#686868"}}],xAxes:[{ticks:{fontColor:"#686868"},gridLines:{display:!1,drawBorder:!1}}]},
elements:{point:{radius:0}}}})
	}})}(jQuery);
*/

$(function () {
});

function chart(idtache){
    var r= document.getElementById("lineChart").getContext("2d");
    // var r= document.getElementsByClassName("lineChart").getContext("2d");
    $("#idtache").val(idtache);
	var linechart= new Chart(r,{type:"line",
	data:{labels:[],
	datasets:[
	{label:"valeurrealisee",data:[],borderColor:["#1d84c6"],
	borderWidth:3,fill:!1,pointBackgroundColor:"#ffffff",pointBorderColor:"#1d84c6"},

	{label:"valeurattendue",data:[],
    // borderWidth:3,fill:!1,pointBackgroundColor:"#ffffff",pointBorderColor:"#FF0909"}
    fill:!1,backgroundColor:"#FF0909",borderColor:"#FF0909"}
	]},

	/*options:{scales:{yAxes:[{gridLines:{drawBorder:!1,borderDash:[3,3]},ticks:{min:0}}],
	xAxes:[{gridLines:{display:!1,drawBorder:!1,color:"#ffffff"}}]},elements:{line:{tension:.2},
	point:{radius:4}},stepsize:1}*/

   options: {
				responsive: true,
				title: {
					display: true,
					text: ''
				},
				tooltips: {
					mode: 'dataset',
					// intersect: true,
				},
				hover: {
					mode: 'dataset',
					// intersect: true
				},
				scales: {
					xAxes: [{
						display: true,
						scaleLabel: {
							display: true,
							labelString: 'Période'
						}
					}],
					yAxes: [{
						display: true,
						scaleLabel: {
							display: true,
							labelString: 'Value'
						}
					}]
				}
	}

	});

	/*linechart.data.datasets.splice(0, 2);
	linechart.update();*/
	$("#spinner1").show();
	ajax_chart2(linechart,"http://localhost/business-plan/public/taches/graphOfIndicateurs?idtache="+idtache);
	// ajax_chart2(linechart,"http://localhost/business-plan/public/taches/graphOfIndicateurs?idtache="+idtache);
	$('#chartModal').modal();


}

/*function ajax_chart(chart, url){
	// var data = data || {};
	var valeurrealisee=[];
	var valeurattendue=[];
	var labels=[];

	$.getJSON(url).done(function(response) {
            labels = response.labels;
            valeurrealisee = response.valeurrealisee; // or you can iterate for multiple datasets
            valeurattendue = response.valeurattendue; // or you can iterate for multiple datasets

			//console.log(chart.data.datasets);
            //chart.update(); // finally update our chart
    });

}*/
function ajax_chart2(chart, url){
	// var data = data || {};
	/*$.getJSON(url).done(function(response) {

    });*/

	$.ajax({
			url: url,
			// data: data,
			type: "get",
			success: function(response){
				chart.data.labels = response.labels;
				chart.options.title.text = response.tache.nom;
				chart.data.datasets[0].data = response.valeurrealisee; // or you can iterate for multiple datasets
				//if(chart.data.datasets.length>1){
				if(chart.data.datasets.length>1){
				chart.data.datasets[1].data = response.valeurattendue;
                chart.data.datasets.splice(1, 1);
				}
				console.log(chart.data.datasets);
				console.log(response.valeurattendue);

				chart.update(); // finally update our chart
				$("#spinner1").hide();

			}
	});
	// chart.update();

}
