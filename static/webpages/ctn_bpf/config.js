        $(document).ready(function () {
            $("#savePeriodeDecoupage").click( function(e) {
            var data=$("#form-decoupage").serialize();
            console.log(data);

                $.ajax({
                        url: base_url+"config/saveperiodedecoupage",
                        beforeSend: function() {$("#spinner").show();},
                        data: data,
                        type: "get",
                        success: function(res){
                            console.log(res);
                            $("#detail").hide();
                            if($("#idDecoupage").val()==0){
                                console.log("he");
                             $("#decoupages > tbody").append("<tr id='tr-"+res.id+"'><td>"+res.libelle+"</td><td>"+res.rang+"</td><td>"+res.description+"</td><td>"+res.datedebut+"</td><td>"+res.datefin+"</td><td><a onclick='editPeriodeDecoupage("+res.id+")' href='#'><i class='fas fa-pencil-alt'></i></a></td></tr>");
                            } else {
                             var row=$("#decoupages > tbody").find("#tr-"+res.id);
                             row.replaceWith("<tr id='tr-"+res.id+"'><td>"+res.libelle+"</td><td>"+res.rang+"</td><td>"+res.description+"</td><td>"+res.datedebut+"</td><td>"+res.datefin+"</td><td><a onclick='editPeriodeDecoupage("+res.id+")' href='#'><i class='fas fa-pencil-alt'></i></a></td></tr>");

                            }
                            $("#spinner").hide();

                        }
                });

        });

        });


            function editcolor(id){
				console.log(id);
				href=base_url+"config/editColor?id="+id;
				$.get(href, function(res){
						$("#valeur").val(res.valeur);
						$("#min").val(res.min);
						$("#max").val(res.max);
						$("#idColor").val(res.id);
						// $("#component-colorpicker").colorpicker({color:'#ccc'});
						$('#component-colorpicker i').css('backgroundColor', res.valeur);


				});
				$('#colorModal').modal();
			}

			$(document).ready(function () {
			$("#component-colorpicker").colorpicker({format:null});
            });

            function addParamEtat(){
                $('#addParamEtatModal').modal();
            }


            function editPeriode(id){
                $('#editPeriode').modal();
                href=base_url+"config/editPeriode?id="+id;
				$.get(href, function(res){
                        $("#periode").val(res.libelle);
                        $("#sousperiode").val(res.sousperiode);
                        $("#typeperiodeDecoupage").val(res.id);
                        $("#decoupages > tbody").empty();
                        for(var i=0; i<res.periodes.length; i++){
                            $("#decoupages > tbody").append("<tr id='tr-"+res.periodes[i].id+"'><td>"+res.periodes[i].libelle+"</td><td>"+res.periodes[i].rang+"</td><td>"+res.periodes[i].description+"</td><td>"+res.periodes[i].datedebut+"</td><td>"+res.periodes[i].datefin+"</td><td><a onclick='editPeriodeDecoupage("+res.periodes[i].id+")' href='#'><i class='fas fa-pencil-alt'></i></a></td></tr>");
                        }



                });

            }




            function editPeriodeDecoupage(id){
                $("#detail").toggle();
                $("#idDecoupage").val(id);

                if(id==0){
                    document.getElementById("form-decoupage").reset();

                } else {
                href=base_url+"config/editPeriodeDecoupage?periode="+id;
				$.get(href, function(res){
                        $("#libelleDecoupage").val(res.libelle);
                        $("#rangDecoupage").val(res.rang);
                        $("#datedebutDecoupage").val(res.datedebut);
                        $("#datefinDecoupage").val(res.datefin);
                        $("#descriptionDecoupage").val(res.description);




                });
            }

            }

            function affectUsertoInstitution(id){
                $('#affectInstitutiontoUser').modal();
                href=base_url+"config/editInstitution?id="+id;
				$.get(href, function(res){
                        $("#idInstitution").val(res.idinstitution);
                        $("#userInstitution").val(res.users);


                });

            }
            function editInstitution(id){

                $("#idInstitution").val(id);
                $("#nomInstitution").val("");
                $("#codeInstitution").val("");
                $("#periodeInstitution").val("");
                $("#modeindicateur").val("");

            if(id!=0){
				href=base_url+"config/editInstitution?id="+id;
				$.get(href, function(res){
                        $("#nomInstitution").val(res.nom);
                        $("#codeInstitution").val(res.code);

                        $("#idInstitution").val(res.idinstitution);
                        $("#periodeInstitution").val(res.periodes);
                        //$("#logo").val(res.logo);
                        $("#modeindicateur").val(res.modeindicateur.valeur);


                        console.log(res.modeindicateur.valeur);

                        $("#previewlogo").html("<img src='"+base_url+"fileconfig/logo/"+res.logo+"'/>");


                });
            }
                $('#addInstitutionModal').modal();

            }

            function editparamEtat(id){
				console.log(id);
				href=base_url+"config/editparamEtat?id="+id;
				$.get(href, function(res){
						$("#title").val(res.title);
						$("#subtitle").val(res.subtitle);
                        $("#rang").val(res.rang);
						$("#lang").val(res.lang);

						$("#idinstitution").val(res.idinstitution);
						// $("#component-colorpicker").colorpicker({color:'#ccc'});


				});
				$('#addParamEtatModal').modal();
			}
