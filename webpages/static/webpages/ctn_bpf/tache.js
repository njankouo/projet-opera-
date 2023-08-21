	function addTache(){
				document.getElementById("addFormTache").reset();
			}

	function editTache(id){
				href=base_url+"config/editTache?id="+id;
				$.get(href, function(res){
						// console.log(res);
						// console.log(res.nom);
						$("#codeAct").val(res.code);
						$("#nomAct").val(res.nom);
						$("#idstructureTache").val(res.idstructure);
						$("#indicateurspoursuivisTache").val(res.indicateurspoursuivis);
						$("#totalmontantaloueTache").val(res.totalmontantaloue);
						$("#valeurattendueTache").val(res.valeurattendue);
						$("#idactiviteTache").val(res.idactivite);
						$("#indicateurresultTache").val(res.indicateurresult);
						$("#idAct").val(res.idtache);

				});
				$('#addTacheModal').modal();
	}


	function deleteTache(id){
				//href=base_url+"config/editTache?id="+id;
				$("#idtache").val(id);
				/*$.get(href, function(res){
						console.log(res);
						console.log(res.nom);
						$("#nomAct").val(res.nom);
						$("#idstructureAct").val(res.idstructure);
						$("#indicateurspoursuivisTache").val(res.indicateurspoursuivis);
						$("#totalmontantaloueTache").val(res.totalmontantaloue);
						$("#valeurattendueTache").val(res.valeurattendue);
						$("#idactiviteTache").val(res.idactivite);
						$("#indicateurresultTache").val(res.indicateurresult);
						$("#idAct").val(res.idtache);

				});*/
				$('#deleteTacheModal').modal();
	}

	function deleteActivite(id){
				//href=base_url+"config/editTache?id="+id;
				$("#idactivite").val(id);

				$('#deleteActiviteModal').modal();
	}

	function deleteAction(id){
				$("#idaction").val(id);
				$('#deleteActionModal').modal();
	}

	function deleteProgramme(id){
				$("#idprogramme").val(id);
				$('#deleteProgrammeModal').modal();
	}



	function planning(id){
				href=base_url+"config/editTachePlanning?idtache="+id;
				document.getElementById("form-planning").reset();

				$("#idtache").val(id);
				$("#spinner1").show();


				$.ajax({
						url: href,
						// data: data,
						type: "get",
						beforeSend : function(){
							$("#spinner1").show();
						},
						success: function(res){
							console.log(res.data);
							for(var i=0; i<res.data.length; i++){
							  //console.log(res[i]);
							  //console.log(res);
							  if(res.data[i]==1){
								$( "#"+i ).prop( "checked", true );
							  } else {
								$( "#"+i ).prop( "checked", false );
							  }
							}

							$("#tache-title").text(res.tache.nom);
							$("#spinner1").hide();

						}
				});
				$('#planningModal').modal();
	}



				// table= $('#example').DataTable( {});
	function actCorr1(id, period){
				href=base_url+"taches/activitescorrectrices?tache_id="+id+"&periode_id="+period;
				tache_id=id;
				periode_id=period;
				$('#example').addClass("tab"+id);


				$.get(href, function(task){
					console.log(task.data);
					chronos=task.data;
					periodestache=task.periodestache;
					var columns=[{ data: 'code' },{ data: 'operation' },{ data: 'nompersonnel'} ,{ data: 'montant' }];

					let initialValue = 0;
					const reducer = (accumulator, currentValue) => accumulator + currentValue.montant;
					//console.log();
					$("#totalmontant").text(chronos.reduce(reducer, initialValue));

					for(var i=0; i<task.periode.length;i++){
						// columns.push({ data: " "+periode[i] });
						columns.push({ data: " "+task.periode[i].data });
					}
					columns.push({ data: 'action' });

					if(datatable!=undefined){
						datatable.ajax.url( href ).load();
					}

					//if(chronos.length>0) {
					if(chronos.length>0) {
					chrono=chronos[0].chrono;
					periode=chronos[0].periode;
					}
					var data;
					// var columns=[{ data: 'id' },{ data: 'operation' },{ data: 'montant' }];


					$("#tache-title").text(task.tache.nom);
					$("#tache-result").text(task.tache.indicateurresult);


					/*for(var i=0; i<task.periodestache.length;i++){
						// columns.push({ data: " "+periode[i] });
						//columns.push({ data: " "+task.periode[i].data });
						$('.selector').append('<div class="custom-control custom-checkbox">'
						+'<input type="checkbox" class=" checkbox custom-control-input" name="periode_id" value="'+task.periodestache[i].id+'"  required />'
						+'<label class="custom-control-label">'+task.periodestache[i].libelle+'</label></div>');
					}*/

					//if(datatable==undefined){
						 datatable= $('.chronotable').DataTable( {
						 // datatable= $(".tab"+id).DataTable( {
						  "ajax": {
							"type":"get",
							"url":href,
							"dataSrc": function(res) {
								console.log(res);
								chronos=res.data;

								return res.data;
							},
						  },

						  "columns": columns,
						  "searching": false,
						  "lengthChange":false,
						  "bDestroy": true,
						  "createdRow": function(row, data, dataIndex ) {
								if (data.statut == 0 ) {
								  $(row).addClass('table-danger');
								}
								if (data.statut == 1 ) {
								  $(row).addClass('table-success');
                                }
                                if (data.etat == 1 ) {
                                    $(row).addClass('text-primary');
                                }
                                if (data.etat == 0 ) {
                                    $(row).addClass('text');
                                }

						   }
						});
					// }

					/*} else {
						if(datatable==undefined){
						  datatable=$('#example').DataTable({"columns": columns,
							"searching": false, "lengthChange":false,});
						}
					}*/

					$("#example").on('mousedown.edit', "i.fa.fa-pencil-alt", function(e) {
						 //
						// $(this).removeClass().addClass("fa fa-envelope-square");
						const t = chronos.find(t => t.id == this.id);
						console.log(t);
                        $('#form-chrono #code').val(t.code);
						$('#form-chrono #poids').val(t.poids);

						$('#form-chrono #operation').val(t.operation);
						$('#form-chrono #montant').val(t.montant);
						$('#form-chrono #idpersonnel').val(t.idpersonnel);
						$('#form-chrono #id').val(t.id);
						$('#form-chrono #tache_id').val(id);
						$('#form-chrono #periode_id').val(periode_id);

						if(chronos.length>0) {
								periode=chronos[0].periode;
						}
						for(var i=0; i<periode.length;i++){
							var v=" "+periode[i];
						 if(t[v]!=""){
						   $('#form-chrono #input-'+periode[i]).prop("checked", true);
						   $('#form-chrono #hinput-'+periode[i]).val("1");
						 } else {
						   $('#form-chrono #input-'+periode[i]).prop("checked", false);
						   $('#form-chrono #hinput-'+periode[i]).val("0");
						 }

						 console.log(t[v]);
						// alert(eval(v));
						}
						// $("#detail").toggle();
						console.log("t[v]");
                        $("#detail").toggle();
						$("#detail-file").hide();


					});

					$(".form-chrono").find("checkbox").each(function(){
						console.log("hello");
						if ($(this).prop('checked')==true){
							//do something
							$(this).val("1");

						} else {
							$(this).val("0");
						}
					});





				});
	}

	function actCorr(idtache,period){
		actCorr1(idtache, period);
		$('#addModal').modal();


	}

	  /** format for dataTache **/
    function formatTache ( idtache, periodes ) {
                // `d` is the original data object for the row

				var data='';
				var period=$('#typeperiode').val();
				/* console.log(d);*/
				for(var i=0; i<periodes.length;i++){
				data +='<th>'+periodes[i].libelle+'</th>';
				// console.log(periodes[i]);
				}

				actCorr1(idtache, period);
                return '<table data-paging="false" data-info="false" data-responsive="responsive" class=" chronotable table-bordered display     float-left " cellspacing="0" width="85%">'
				+	'<thead><tr role="row"><th rowspan="2"  data-visible="false"></th>'
				+'<th rowspan="2" >Opérations</th>'
				+'<th rowspan="2" >Personnel</th>'
				+'<th rowspan="2">Montant</th>'
				+'<th colspan="'+periodes.length+'" rowspan="1">Chronogramme de mise en oeuvres</th>'
				+'<th rowspan="2" data-visible="false">Actions</th>'
				+'</tr><tr role="row">'
				+data
				+'</tr>'
                +'</thead></table>';
    }


	function closeModal(){
			  $('#example').removeClass("tab"+tache_id);
	}





	$(document).ready(function () {

		var tabletache= $('#tache').DataTable({
                  initComplete: function () {
                        var api = this.api();
                        //console.log( $('#modeindicateur').val());
                        if ( $('#modeindicateur').val()=="auto" ) {
                        // Hide Office column
                        api.column(5).visible( false );
                        api.column(6).visible( false );
                        }
                  },
                  ajax:{
                  type:"get",
                  data:{"structure": $('#structure').val(),"typeperiode": $('#typeperiode').val(), "annee": $('#annee').val()},

                  url: base_url+"taches/filtertachesjson"},
				  searching: true, "lengthChange":false,
				   'columns': [
					 {
                        "className":      'details-control',
                        "orderable":      false,
                        "data":           null,
                        "defaultContent": ''
                    },

					{ "data": "activite" },
                    { "data": "nom" },
                    { "data": "indicateurresult" },
					{ "data": "indicateurspoursuivis" },
					{ "data": "valeurattendue" },
					{ "data": "valeurrealisee" },//fonction de la periode
					{ "data": "gap" },

					{ "data": "justification" },


					{ "data": "budgetutilise" },
					{ "data": "chronogramme" },
					{ "data": "chart" },

					],
					"order": [[1, 'asc']]
		});


		$('#tache tbody').on('click', 'td.details-control', function () {
                        var tr = $(this).closest('tr');
                        var row = tabletache.row( tr );

                        if ( row.child.isShown() ) {
                            // This row is already open - close it
                            row.child.hide();
                            tr.removeClass('shown');
                        }
                        else {
                            // Open this row
                            console.log(row.data())
                            row.child( formatTache(row.data().idtache, row.data().periodes) ).show();


                            tr.addClass('shown');
                        }
        });


		tabletache.MakeCellsEditable({
					"onUpdate": myCallbackFunction,
					"inputCss":'my-input-class',
					"columns": [6,8],
					"allowNulls": {
						"columns": [3],
						"errorClass": 'error'
					},
					"confirmationButton": { // could also be true
						"confirmCss": 'my-confirm-class',
						"cancelCss": 'my-cancel-class'
					},
					"inputTypes": [
						{
							"column": 6,
							"type": "text",
							"options": null
						},
						{
							"column": 8,
							"type": "textarea",
							"options": null
						},
						 // Nothing specified for column 3 so it will default to text

					]
		});

		function myCallbackFunction (updatedCell, updatedRow, oldValue) {
					console.log("The new value for the cell is: " + updatedCell.data());
					console.log("The old value for that cell was: " + oldValue);
					var data=updatedRow.data();
					data.typeperiode=$("#typeperiode").val(); //period_id

					console.log(updatedRow.data());

					//
					$.ajax({
								url: base_url+"taches/updatetachetext",

								data: data,
								type: "get",
								success: function(result){
									console.log(result);
									tabletache.ajax.reload();

								}
					 });
		}

		$(".form-chrono .checkbox").click(function() {
					   console.log('jj');
					    var id=$(this).attr('id');
					     console.log(id);
					   if ($(this).prop('checked')==true){
							//do something

							$("#h"+id).val("1");

						} else {
							$("#h"+id).val("0");
						}
		});





		$("#addChrono").click( function(e) {
						// console.log("dd1");
						$('#form-chrono').find("input[type=text]").each(function(i, v) {
							$(this).val("");
							// console.log("dd");
						});
						$('#form-chrono #id').val("");
						$('#form-chrono #tache_id').val(tache_id);
						$('#form-chrono #periode_id').val(periode_id);
						$("#detail").show();
        });


        $("#saveFile").click( function(e) {

            var formData = new FormData();
            formData.append('file', $('#fichier')[0].files[0]);
            formData.append("activitecorrectrice_id", $('#operation_id').val());
            formData.append("nom", $('#nomfile').val());

            //console.log($('input[name="_token"]').val());

            $.ajax({
                url : base_url+"taches/saveoperationfile",
                headers: {'X-CSRF-TOKEN': $('input[name="_token"]').val()},
                type : 'POST',
                data : formData,
                processData: false,  // tell jQuery not to process the data
                contentType: false,  // tell jQuery not to set contentType
                success : function(data) {
                    console.log(data);
                   /// alert(data);
				   $("#detail-file").toggle();
                },
                error: function(jqXHR, textStatus, errorMessage) {
                    console.log(errorMessage); // Optional
                }
            });


        });

		$("#saveChrono").click( function(e) {
					var data=$("#form-chrono").serializeArray();
					var data2=$("#form-chrono").serialize();
					var id=data.find(t => t.name == "id").value;
					//if(id!=""){ //mode edition
						// var t = chronos.find(t => t.id == id);
						// t.operation=data.find(t => t.name == "operation").value;
						console.log(data2);
						// console.log(chronos);

						 $.ajax({
								url: base_url+"taches/saveactivitescorrectrice",
								beforeSend: function() {$("#spinner").show();},
								data: data2,
								type: "get",
								success: function(result){
									console.log(result);
									$("#detail").hide();
									datatable.ajax.reload();
									tabletache.ajax.reload();
									$("#spinner").hide();

								}
						  });

		});


		$("#saveChart").click( function(e) {
					var data=$("#form-chart").serializeArray();
					var data2=$("#form-chart").serialize();
					//var id=data.find(t => t.name == "id").value;
					//if(id!=""){ //mode edition
						// var t = chronos.find(t => t.id == id);
						// t.operation=data.find(t => t.name == "operation").value;
						//console.log(data2);
						// console.log(chronos);

						 $.ajax({
								url: base_url+"taches/saveDataIndicateur",
								beforeSend: function() {$("#spinner").show();},
								data: data2,
								type: "get",
								success: function(result){
									console.log(result);
									//$("#detail").hide();
									tabletache.ajax.reload();
									chart($("#idtache").val())
									$("#spinner").hide();

								}
						  });

		});


		$("#savePlanning").click( function(e) {
					//var data=$("#form-chart").serializeArray();
					var data2=$("#form-planning").serialize();
					//var id=data.find(t => t.name == "id").value;
					//if(id!=""){ //mode edition
						// var t = chronos.find(t => t.id == id);
						// t.operation=data.find(t => t.name == "operation").value;
						//console.log(data2);
					//console.log(data2);

					$.ajax({
								url: base_url+"config/tachestoperiode",
								beforeSend: function() {$("#spinner").show();},
								data: data2,
								type: "get",
								success: function(result){
									console.log(result);
									$("#spinner").hide();
									tabletacheconfig.ajax.reload();
									$('#planningModal').modal('toggle');

								}
					});

		});

		$("#saveReprog").click( function(e) {
					//var data=$("#form-chart").serializeArray();
					var data2=$("#form-reprog").serialize();
					//var id=data.find(t => t.name == "id").value;
					//if(id!=""){ //mode edition
						// var t = chronos.find(t => t.id == id);
						// t.operation=data.find(t => t.name == "operation").value;
						//console.log(data2);
					console.log(data2);

					$.ajax({
								url: base_url+"taches/reprogoperation",
								beforeSend: function() {$("#spinner").show();},
								data: data2,
								type: "get",
								success: function(result){
									console.log(result);
									$("#spinner").hide();
									$("#detail-reprog").toggle();
									// datatable.ajax.reload();
									// $('#planningModal').modal('toggle');

								}
					});

        });



        $("#saveRealtechnotif").click( function(e) {
            //var data=$("#form-chart").serializeArray();
            var data2=$("#form-realtech").serialize();
            console.log(data2);

            $.ajax({
                        url: base_url+"taches/realtech",
                        beforeSend: function() {$("#spinner").show();},
                        data: data2,
                        type: "get",
                        success: function(result){
                            console.log(result);
                            $("#spinner").hide();
                            $("#detail-realtech").toggle();

                        }
            });

});

$("#saveRealtech").click( function(e) {
    //var data=$("#form-chart").serializeArray();
    var data2=$("#form-realtech").serialize();
    //console.log(data2);

    $.ajax({
        url: base_url+"taches/changeStatutactivitescorrectrice",
        beforeSend: function() {$("#spinner").show();},
        data: data2,
        type: "get",
        success: function(result){
            console.log(result);

            datatable.ajax.reload();
            tabletache.ajax.reload();
            // $("#totalmontant").text(chronos.reduce(reducer, initialValue));
            $("#spinner").hide();
            $("#detail-realtech").toggle();

        }
  });

});









				  // config tache
		var tabletacheconfig = $('#tacheconfig').DataTable({
			   'ajax': base_url+'config/tachesjson?annee='+$('#annee').val(),

			  /*'columnDefs': [
				 {
					'targets': 0,
					'checkboxes': {
					   'selectRow': true
					}
				 }
			  ],*/
			  /*'columns': [
					{ "data": "idtache" },
					{ "data": "activite" },
					{ "data": "nom" },
					{ "data": "periode_id" },
					{ "data": "periode_id" },
					{ "data": "periode_id" },
					{ "data": "periode_id" },
				],
				'columnDefs': [
				 {
					'targets': 0,
					'checkboxes': {
					   'selectRow': true
					}
				 }
			  ],
			  'select': {
				 'style': 'multi'
			  },*/
			   'order': [[0, 'asc']],
			   "lengthChange":false,
			  /*"initComplete": function(settings, json) {
				initCompleteTacheConfig();
			  }*/
		});
		// $(".switchery").each(function(a,e){new Switchery($(this)[0],$(this).data())});

		   /////////////////////////////////////////
		$("#example").on('mousedown.remove', "i.fa.fa-minus-square", function(e) {
						console.log("hello");
						const t = chronos.find(t => t.id == this.id);
						console.log(t);
						 $.ajax({
								url: base_url+"taches/removeactivitescorrectrice",
								beforeSend: function() {$("#spinner").show();},
								data: t,
								type: "get",
								success: function(result){
									console.log(result);
									datatable.ajax.reload();
									tabletache.ajax.reload();
									// $("#totalmontant").text(chronos.reduce(reducer, initialValue));
									$("#spinner").hide();

								}
						  });

		});

			/////////////////////////////////////////
		$("#example").on('mousedown', "i.mdi.mdi-alpha-t-circle", function(e) {
                        console.log("hello");
                        $('#operation_realtech').val(this.id);
			            //$('#idoperation').text(this.id);
                        $("#detail-realtech").toggle();
						const t = chronos.find(t => t.id == this.id);
						console.log(t);
						 /*$.ajax({
								url: base_url+"taches/changeStatutactivitescorrectrice",
								beforeSend: function() {$("#spinner").show();},
								data: t,
								type: "get",
								success: function(result){
                                    console.log(result);

									datatable.ajax.reload();
									tabletache.ajax.reload();
									// $("#totalmontant").text(chronos.reduce(reducer, initialValue));
									$("#spinner").hide();

								}
						  });*/

        });

        /////////////////////////////////////////
		$("#example").on('mousedown', "i.mdi.mdi-paperclip", function(e) {
            console.log("hello");
            const t = chronos.find(t => t.id == this.id);
            console.log(t.medias);
            $("#codeoperation").text(t.code);

            $("#operation_id").val(this.id);
            $("#detail").hide();
            $('#listfichier').empty();

            t.medias.forEach(m => {
                $("#listfichier").append('<li><a  href="fichiers/operations/'+m.fichier+'" target="_BLANK"> '+
                m.nom+'</a></li>');
            });



            $("#detail-file").toggle();


        });

        /////////////////////////////////////////
		$("#example").on('mousedown', "i.mdi.mdi-alpha-f-circle", function(e) {
            console.log("hello");
            const t = chronos.find(t => t.id == this.id);
            console.log(t);
             $.ajax({
                    url: base_url+"taches/changeEtatactivitescorrectrice",
                    beforeSend: function() {$("#spinner").show();},
                    data: t,
                    type: "get",
                    success: function(result){
                        console.log(result);
                        datatable.ajax.reload();
                        tabletache.ajax.reload();
                        // $("#totalmontant").text(chronos.reduce(reducer, initialValue));
                        $("#spinner").hide();

                    }
              });

        });
           /////////////////////////////////////////
		$("#example").on('mousedown', "i.fas.fa-exchange-alt", function(e) {
            // console.log(this.id);
            //const t = chronos.find(t => t.id == this.id);
            // console.log(tache_id);
			$('#tache_idprog').val(tache_id);
			$('#idoperation').text(this.id);
			$('.selector').html("");
			var html='Periode';
			html+='<select class="form-control" name="periode_id" required>';
            for(var i=0; i<periodestache.length;i++){
						// columns.push({ data: " "+periode[i] });
						//columns.push({ data: " "+task.periode[i].data });
						html+='<option   value="'+periodestache[i].id+'"   >'
						+periodestache[i].description+'</option>';
			}
			html+="</select>";
			$('.selector').html(html);
			$('.operation').html('<input type="hidden" class="form-control" value="'+this.id+'"name="activite_id" id="op"  />');
			$("#detail-reprog").toggle();

        });


	function initCompleteTacheConfig(){
		//alert( 'DataTables has finished its initialisation.' );

		$(".switchery-periode").change(function(){
					// alert('hi');
			console.log('Clicked '+$(this).val());
			affecterperiodetache($(this).val());
		});

	}


	   // Affecter Tache Periode
	function affecterperiodetache(id){

		idtache=id.split("-")[0];
        idperiode=id.split("-")[1];
		libelleperiode=id.split("-")[2];

		 $.ajax({
			type: 'GET',
			url: base_url+'config/tachestoperiode',
			data: {'id':idtache, 'periode':idperiode},
			beforeSend: function() {
				$("#spinner").show();

			},
			success: function(data) {
				console.log(data);
                //$("#result").text(data);
                var res="Planification";
                var color="success";
                if(data=="0"){
                    res="Déplanification";
                    color="warning";
                }
				tabletacheconfig.ajax.reload(initCompleteTacheConfig);
                var msg='<div class="alert alert-'+color+' alert-dismissible fade show mb-0" role="alert">'+
                '<strong>'+res+' Ok!</strong> Tache N° '+idtache+' pour à la période '+libelleperiode+
                '<button type="button" class="close" data-dismiss="alert" aria-label="Close">'+
                ' <span aria-hidden="true">×</span>'+
                '</button>'+
                ' </div>';
                $("#spinner").hide();
				$("#confirm").append(msg);

			}
		 });

	   }


	});
