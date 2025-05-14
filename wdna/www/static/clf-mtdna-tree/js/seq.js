function init_seq(){
    'use strict';
        var grid = $("#sequences");
    
        grid.jqGrid({
                url: "data/sequences.json",
                datatype: "json",
                loadonce: true,
            colModel: [
                { key:true, name: 'GenBank accession number', index: 'GenBank accession number', width: "100" , 
                    formatter: 'showlink', formatoptions: {baseLinkUrl:'http://www.ncbi.nlm.nih.gov/nuccore/',idName:'term'}},
                { name: 'Haplogroup', index: 'Haplogroup', width: "100"},
                { name: 'Region', index: 'Region', width: "100"},
                { name: 'Subsubregion', index: 'Subsubregion', width: "80" },
                { name: 'Author', index: 'Author', width: "100" },
                { name: 'Source', index: 'Source', width: "400" },
                { name: 'Breed of dog', index: 'Breed of dog', width: "200"},
                { name: 'Group', index: 'Group', width: "150" },
                { name: 'Section', index: 'Section', width: "150" },
                { name: 'Subsection', index: 'Subsection', width: "150" },
                { name: 'Country of origin of the breed', index: 'Country of origin of the breed', width: "150" },
                { name: 'Comments', index: 'Comments', width: "200" }
            ],
            pager: '#sequencePager',
            jsonReader: { 
                repeatitems: false,
                root: function(obj) { return obj; },
                id: "GenBank accession number"
            },
            rowNum: 25,
            viewrecords: true,
            caption: "Breed explorer",
            height: "auto",
            ignoreCase: true,
            shrinkToFit: false,
            autowidth: true,
            width: 1600,
            loadComplete: function() {
                $(this).trigger('jqGridLoadComplete');
            },
            afterFilterSearch: function() {
                $(this).trigger('jqGridToolbarFilterClicked');
            }
        });
        grid.jqGrid('navGrid', '#sequencePager',
            { add: false, edit: false, del: false }, {}, {}, {},
            { multipleSearch: true, multipleGroup: true });
        grid.jqGrid('filterToolbar', { 
            defaultSearch: 'cn', 
            stringResult: true, 
            searchOnEnter: false,
            afterSearch: function() {
                grid.trigger('jqGridToolbarFilterClicked');
            }
        });

        grid.on('jqGridAfterGridComplete', function() {
            $(this).trigger('jqGridAfterLoadComplete');
        });
}