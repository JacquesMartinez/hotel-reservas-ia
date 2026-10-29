var resourceModule = angular.module('resourceModule', ['ngResource']);

resourceModule.factory('authFactory', function($resource){
	return $resource('/api', {}, {
		Register: {
			method: 'POST',
			url: '/api/register'
		},
		Login: {
			method: 'POST',
			url: '/api/login'
		}

	})
})

resourceModule.factory('reportFactory', function($resource){
	return $resource('/api', {}, {
			ResReport: {
				method: 'GET',
				url: '/api/reports/reservation'
			},
			PopularRoomCatReport: {
				method: 'GET',
				url: '/api/reports/popularRoom'
			},
			RevenueReport: {
				method: 'GET',
				url: '/api/reports/revenue'
			},
			Forecast: {
				method: 'GET',
				url: '/api/reports/forecast'
			}
	})
})

resourceModule.factory('reservationFactory', function($resource){
	return $resource('/api', {}, {
		SearchRooms:{
			method: 'GET',
			url: '/api/searchRoom'
		},
		GetAvailability:{
			method: 'GET',
			url: '/api/availability'
		},
		GetReservation:{
			method:'GET',
			url: '/api/reservation/:reservation_id'
		},
		GetMyReservations:{
			method:'GET',
			url: '/api/reservations',
			isArray: true
		},
		MakeReservation: {
			method: 'POST',
			url: '/api/reservation/create'	
		},
		UpdateReservationConfirm:{
			method: 'GET',
			url: '/api/reservation/:reservation_id/availability'
		},
		UpdateReservation:{
			method:'PUT',
			url: '/api/reservation/:reservation_id'
		},
		CancelReservation:{
			method:'GET',
			url: '/api/reservation/:reservation_id/cancel'
		}
	})
})

resourceModule.factory('reviewFactory', function($resource){
	return $resource('/api', {}, {
		AddReview:{
			method: 'POST',
			url: '/api/review'
		},
		GetReviews:{
			method: 'GET',
			url: '/api/review',
			isArray: true
		}
	})
})

resourceModule.factory('paymentFactory', function($resource){
	return $resource('/api', {}, {
		GetCreditCards:{
			method: 'GET',
			url: '/api/payment',
			isArray: true
		},
		AddCreditCard:{
			method: 'POST',
			url: '/api/payment'
		},
		DeleteCreditCard:{
			method: 'DELETE',
			url: '/api/payment'
		},
		SetDefaultCreditCard:{
			method: 'POST',
			url: '/api/payment/default'
		},
		GetReservationByCardNumber:{
			method: 'GET',
			url:'/api/reservation/cardNumber',
			isArray: true //returns an array
		}
	})
})


//the server's reason for a failed request; reqparse errors come as {"field": "help"}
function errorMessage(errorData, fallback){
	var message = errorData.data && errorData.data.message;
	if(message && typeof message === 'object'){
		message = Object.keys(message).map(function(key){ return message[key]; }).join(' ');
	}
	return message || fallback;
}

angular.module('FancyHotelApp', ['ngRoute', 'ngResource', 'resourceModule'])

.run(function($rootScope, $http, $route, $location) {
    $rootScope.currentUser = '';
	$rootScope.userType = '';
	$rootScope.alreadyLoggedIn = function(){
		if($rootScope.currentUser != ''){
			console.log("you're already logged in.")
			return true;
		}
		console.log("you're not logged in yet.")
		return false;
	}

	$rootScope.getUserType = function(){
		var userType = $rootScope.currentUser.charAt(0);
		if(userType == 'M' || userType == 'm' ){
			$rootScope.userType = "manager";
		}
		else if(userType == 'C' || userType == 'c'){
			$rootScope.userType = "customer";
		}
		else{
			$rootScope.userType = "invalid user type";
		}
	}

	$rootScope.isRequired = true;

	//the session lives on the server: recover the user after a page reload
	$http.get('/api/me').then(function(response){
		$rootScope.currentUser = response.data.username;
		$rootScope.userType = response.data.role;
		$route.reload(); //the controllers read loggedInBool when they start, so start them again
	}, function(){}); //401 just means nobody is logged in

	$rootScope.logout = function(){
		$http.post('/api/logout').then(function(){
			$rootScope.currentUser = '';
			$rootScope.userType = '';
			$location.path('/');
		});
	}

})

//any 401 from the API means the session is missing or expired: send the user to the login page
.factory('authInterceptor', function($q, $rootScope, $location){
	return {
		responseError: function(rejection){
			var url = rejection.config && rejection.config.url;
			//login answers 401 for wrong credentials and me answers 401 when nobody is logged in
			if(rejection.status == 401 && url != '/api/login' && url != '/api/me'){
				$rootScope.currentUser = '';
				$rootScope.userType = '';
				$location.path('/login');
			}
			return $q.reject(rejection);
		}
	};
})

.config(function($httpProvider){
	$httpProvider.interceptors.push('authInterceptor');
})


.controller('registerController', function($rootScope, $scope, authFactory, $window) {
	$rootScope.alreadyLoggedIn();
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.confirmPass;
	var usernameFail = false;
	$scope.username = '';
	$scope.myRegex = /C[a-zA-Z0-9]{4}/;

	$scope.submit = function() {
		if($scope.confirmPass !== $scope.password){
			window.alert("Please check your password. There were inconsistencies when you tried to confirm it.");
			console.log("Your passwords don't match.");
			return;
		}
		if($scope.username == undefined || $scope.username.length!=5){
			window.alert("Usernames must be a C followed by 4 characters.");
			console.log("Username wasn't 5 characters");
			return;
		}

		response = authFactory.Register({
			"username": $scope.username,
			"email": $scope.email,
			"password": $scope.password,
			"firstName": $scope.firstName,
			"lastName": $scope.lastName
		}
		, function(successData)
		{
			console.log("account created, being redirected to login screen for official login.");
			$window.location.href='#/login';
		},
		function(errorData)
		{
			//show the server's reason: not every failure is a taken username
			var message = (errorData.data && (errorData.data.error || errorData.data.message)) || "The account could not be created. Please try again.";
			console.log(message);
			window.alert(message);
		});
	}
	
})

.controller('loginController', function($rootScope, $scope, authFactory, $window){
	$rootScope.alreadyLoggedIn();
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();

	$scope.submit = function(){
		response = authFactory.Login({
			"username": $scope.username,
			"password": $scope.password
		},
		function(successData){
			$rootScope.currentUser = $scope.username;
			$rootScope.getUserType();
			console.log("login success!");
			console.log("redirecting...");
			$window.location.href='#/portal';
		},
		function(errorData)
		{
			console.log("login failed");
			window.alert("Invalid credentials");
		});
	}

})

.controller('portalController', function($rootScope, $scope){
	$rootScope.alreadyLoggedIn();
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$rootScope.currentUser;
	$rootScope.getUserType();
	$rootScope.userType;


})
.controller('reservationController', function($rootScope, $scope, $window, $location, reservationFactory, paymentFactory){
	$scope.creditCards; //the number for USING a card
	$scope.creditCardNumber; //the number for ADDING a card
	$scope.cardToDelete; //card you're trying to delete

	var now = new Date();
	var nowplustwo = new Date();
	var nowplusone = new Date();
	nowplusone.setDate(now.getDate()+ 1);
	nowplustwo.setDate(now.getDate() + 2);
	$("#startDatePicker").datetimepicker(
		{
			format: 'YYYY-MM-DD',
			minDate: now,
			date: now
		}
	);
	$("#endDatePicker").datetimepicker(
		{
			format: 'YYYY-MM-DD',
			minDate: nowplusone,
			date: nowplustwo
		}
	);
	
	var occupiedNights = []; //nights (YYYY-MM-DD) with no free room of the selected type in the location
	var availabilityRequest = 0;

	//the check-out may fall on the first occupied night after the check-in, but not later
	function limitCheckOut(checkIn){
		var endPicker = $('#endDatePicker').data("DateTimePicker");
		endPicker.maxDate(false); //cleared first: minDate() throws if it is after maxDate
		if(!checkIn){
			endPicker.minDate(moment().add(1, 'd').startOf('day'));
			return;
		}
		endPicker.minDate(checkIn.clone().add(1, 'd').startOf('day')); //at least one night
		//compared as YYYY-MM-DD strings so no timezone conversion can shift the day
		var checkInDay = checkIn.format('YYYY-MM-DD');
		for(var i = 0; i < occupiedNights.length; i++){
			if(occupiedNights[i] > checkInDay){
				endPicker.maxDate(moment(occupiedNights[i], 'YYYY-MM-DD'));
				return;
			}
		}
	}

	$('#startDatePicker').on("dp.change", function (e) {
		console.log(e);
		limitCheckOut(e.date);
	});

	$('#endDatePicker').on("dp.change", function (e) {
		//the check-in must be at least one night before the check-out
		$('#startDatePicker').data("DateTimePicker").maxDate(e.date ? e.date.clone().subtract(1, 'd').endOf('day') : false);
	});
	
	$("#newStartDate").datetimepicker(
		{
			format: 'YYYY-MM-DD',
			minDate: new Date()
		}
	);
	$("#newEndDate").datetimepicker(
		{
			format: 'YYYY-MM-DD',
			minDate: moment().add(1, 'd').startOf('day'),
			useCurrent: false //keeps the field empty instead of filling it with the minDate
		}
	);

	$('#newStartDate').on("dp.change", function (e) {
		console.log(e);
		//at least one night
		$('#newEndDate').data("DateTimePicker").minDate(e.date ? e.date.clone().add(1, 'd').startOf('day') : moment().add(1, 'd').startOf('day'));
	});

	$('#newEndDate').on("dp.change", function (e) {
		$('#newStartDate').data("DateTimePicker").maxDate(e.date ? e.date.clone().subtract(1, 'd').endOf('day') : false);
	});

	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.viewPart1 = true; //these views are for the update page
	$scope.viewPart2 = false;
	$scope.viewPart3 = false;
	$scope.confirmationPage = false;
	$scope.currRes =''; //this is for the update page
	$scope.newCost = 0;
	$scope.total_cost = 0;
	$scope.cancelView1=true;
	$scope.cancelView2=false;

	$scope.availability={ //this is availability of rooms for an update reservation
		"avail": '',
		"message": ''
	};
	$scope.roomsAvailable = []; //this is rooms available for a new search on rooms, not an upate
	$scope.error = '';
	$scope.hideForm = false;
	$scope.selectedRooms = {};
	$scope.extra_beds = {};
	$scope.location="Atlanta";
	$scope.roomType="Standard";

	$scope.loadAvailability = function(){
		var request = ++availabilityRequest;
		var availabilityResponse = reservationFactory.GetAvailability(
		{
			"location": $scope.location,
			"type": $scope.roomType,
			"from": moment().format('YYYY-MM-DD'),
			"to": moment().add(6, 'months').format('YYYY-MM-DD')
		});
		availabilityResponse.$promise.then(function(data){
			if(request != availabilityRequest){
				return; //the location or type changed again before this response arrived
			}
			occupiedNights = data["occupied"];
			var startPicker = $('#startDatePicker').data("DateTimePicker");
			//parsed with an explicit format: local midnight, never UTC
			startPicker.disabledDates(occupiedNights.map(function(night){
				return moment(night, 'YYYY-MM-DD');
			}));
			var checkIn = startPicker.date();
			if(checkIn && occupiedNights.indexOf(checkIn.format('YYYY-MM-DD')) != -1){
				startPicker.date(null); //the check-in is no longer bookable; dp.change resets the check-out limits
			}
			else{
				limitCheckOut(checkIn);
			}
		},
		function(errorData){
			console.log("Could not load the availability calendar");
		});
	};
	if($("#startDatePicker").length){ //this controller also serves the update and cancel views
		$scope.loadAvailability();
	}

	$scope.creditCards = '';
	//api/blah/blah?username=Csara
	$scope.submit = function(){
		$scope.checkIn = $("#startDatePicker").data("date");
        $scope.checkOut = $("#endDatePicker").data("date");
		
		searchRoomsResponse = reservationFactory.SearchRooms(
		{
			"location": $scope.location,
			"checkIn": $scope.checkIn,
			"checkOut": $scope.checkOut
		});
	//handle promise
		searchRoomsResponse.$promise.then(function(data){
			if(data["result"] == true){
				$scope.roomsAvailable = data["response"];
				$scope.hideForm = true; //hides the form and replaces it with the available rooms
			}
			else{
				$scope.error="Sorry, there are no available rooms for this period of time.";
			}

			getCardsResponse = paymentFactory.GetCreditCards({
				"username": $rootScope.currentUser
			});
			getCardsResponse.$promise.then(function(data){
				$scope.creditCards = data; //data is an array of {token, last4, name, expiration_date, is_default}
				$scope.defaultCard = null;
				for(var i = 0; i < data.length; i++){
					if(data[i].is_default){
						$scope.defaultCard = data[i];
					}
				}
				//the selector starts on the default card, or on the first one if there is no default
				$scope.selectedToken = $scope.defaultCard ? $scope.defaultCard.token : (data.length ? data[0].token : '');
			});
		});
	};
	
	//only an estimate for the user: the server calculates the real total with the prices of the database
	$scope.updateTotalCost = function()
	{
		$scope.total_cost = 0;
		var check_in_raw = $("#startDatePicker").data("DateTimePicker").date();
		var check_out_raw = $("#endDatePicker").data("DateTimePicker").date();
		var check_in = moment([check_in_raw.year(), check_in_raw.month(), check_in_raw.date()]);
        var check_out = moment([check_out_raw.year(), check_out_raw.month(), check_out_raw.date()]);
		var delta = Math.round(moment.duration(check_out.diff(check_in)).asDays());
		for(var key in $scope.selectedRooms)
		{
			if($scope.selectedRooms[key])
			{
				$scope.roomsAvailable.forEach(
					function(room)
					{
						if(room.location + room.room_number === key)
						{
							$scope.total_cost += room.cost;
							if((room.location + room.room_number) in $scope.extra_beds && $scope.extra_beds[room.location + room.room_number])
							{
								$scope.total_cost += room.extra_bed_price;
							}
						}	
					}
				);
			}
		}
		$scope.total_cost *= (delta);
	};
		
	
	//without a token the server uses the default card, so no payment data is asked for
	$scope.bookRooms = function(cardToken){
		if($scope.creditCards=='' || $scope.creditCards.length==0){
			console.log("credit card info required");
			window.alert("Please select a credit card for payment. If you have no credit card, please add one first.");
			return;
		}
		var cardExpireDate;
		var currentToken = cardToken || ($scope.defaultCard && $scope.defaultCard.token);
		for(i=0; i<$scope.creditCards.length; i++){
			if($scope.creditCards[i].token==currentToken){
				cardExpireDate = $scope.creditCards[i].expiration_date;
				break;
			}
		}
		if(!cardExpireDate){
			window.alert("Please select a credit card for payment.");
			return;
		}
		if(cardExpireDate<$scope.checkOut){
			console.log("The card's expiration date is sooner than the checkout date");
			window.alert("You can't use this card because it expires before your stay is done.");
			console.log("Reservation failed");
			return;
		}
		var rooms = []
		for(var key in $scope.selectedRooms)
		{
			if($scope.selectedRooms[key])
			{
				$scope.roomsAvailable.forEach(
					function(room)
					{
						if(room.location + room.room_number === key)
						{
							//no prices are sent: the server takes them from the database (S3)
							var extraBed = (room.location + room.room_number) in $scope.extra_beds && $scope.extra_beds[room.location + room.room_number];
							rooms.push({
								"room_number": room.room_number,
								"location": room.location,
								"extra_bed_or_not": extraBed ? 1 : 0
							});
						}
					}
				);
			}
		}
		
		//rooms
		console.log(rooms);
		if(rooms.length==0){
			window.alert("You must select some room(s) in order to make a reservation.");
			console.log("no rooms selected");
			return;
		}

		var reservation = {
			"username": $rootScope.currentUser,
			"checkIn": $scope.checkIn,
			"checkOut": $scope.checkOut,
			"rooms": rooms
		};
		if(cardToken){
			reservation["card_token"] = cardToken;
		}
		var make_response = reservationFactory.MakeReservation(reservation);
		make_response.$promise.then(function(data)
		{
			console.log(data);
			$scope.confirmationData = data;
			$scope.confirmationPage = true;
		},
		function(errorData)
		{
			//400 (invalid data) or 409 (rooms no longer free): show the server's reason
			var message = errorMessage(errorData, "The reservation could not be created. Please check the data and try again.");
			console.log(message);
			window.alert(message);
		});
	}

	$scope.findReservation = function(){
		getReservationResponse = reservationFactory.GetReservation({
			"reservation_id": $scope.resID,
			"username": $rootScope.currentUser
		});
	//handle promise
		getReservationResponse.$promise.then(function(data){
			if(data["result"] == true){
				$scope.cancelView1=false;
				$scope.cancelView2=true;
				$scope.viewPart2 = true;
				$scope.viewPart1 = false;
				$scope.currRes = data["data"];

				$scope.refund_amount = $scope.refundAmount($scope.currRes.checkin_date, $scope.currRes.total_cost);
				$scope.cancel_cost = $scope.currRes.total_cost - $scope.refund_amount;
			}
			else{
				console.log("The reservation cannot be found. It may not exist, or you may not own it, or it may have been cancelled already.");
				//something about how the reservation doesn't exist
			}
		});
	};


	$scope.searchAvailability = function(){
		$scope.newCheckinDate = $("#newStartDate").data("date");
		$scope.newCheckoutDate = $("#newEndDate").data("date"); 
		var checkin_date_raw = $("#newStartDate").data("DateTimePicker").date();
		var checkout_date_raw = $("#newEndDate").data("DateTimePicker").date();
		var newCheckinDate = moment([checkin_date_raw.year(), checkin_date_raw.month(), checkin_date_raw.date()]);
		var newCheckoutDate = moment([checkout_date_raw.year(), checkout_date_raw.month(), checkout_date_raw.date()]);
		var delta = moment.duration(newCheckoutDate.diff(newCheckinDate)).asDays();
		updateReservationConfirmResponse = reservationFactory.UpdateReservationConfirm({
			"reservation_id": $scope.resID,
			"checkIn": $scope.newCheckinDate,
			"checkOut": $scope.newCheckoutDate,
			"username":$rootScope.currentUser
		},
		function(successData)
		{
			$scope.viewPart3 = true;
			$scope.availability["message"] = "Your selected rooms are available for your newly selected dates. Would you like to confirm your updated reservation?"
			$scope.availability["avail"] = true;
			$scope.newCost = $scope.calculateNewCost(delta, successData.data['rooms']);
		},
		function(errorData)
		{
			//invalid dates or rooms not free: show the server's reason
			window.alert(errorMessage(errorData, "Sorry, but your selected rooms are not available for your newly selected dates."));
		});

	};

	$scope.calculateNewCost = function(time_delta, rooms)
	{
		var total_cost = 0;
		rooms.forEach(function(room)
		{
			total_cost += room.cost;
			total_cost += room.extra_bed_or_not == "1" ? room.extra_bed_price : 0
		});
		return total_cost *= time_delta;
	}

	$scope.updateReservation = function(){
		updateReservationResponse = reservationFactory.UpdateReservation(
		{
			"username":$rootScope.currentUser,
			"reservation_id": $scope.resID,
			"checkIn": $("#newStartDate").data("date"),
			"checkOut": $("#newEndDate").data("date")
		});
		//handle promise
		updateReservationResponse.$promise.then(function(data){
			$window.location.href = "#/portal";
		},
		function(errorData){
			window.alert(errorMessage(errorData, "The reservation could not be updated. Please check the dates and try again."));
		});
	};

	$scope.cancelReservation = function(){
		cancelReservationResponse = reservationFactory.CancelReservation({
			"reservation_id": $scope.resID,
			"username":$rootScope.currentUser
		});

		//also pass in the new cost we give it
	//handle promise
		cancelReservationResponse.$promise.then(function(data){
			if(data["result"]==true){
			console.log("Successfully cancelled reservation.");
			}
			else{
				console.log("This reservation cannot be deleted.")

			}
		});
	};

	$scope.today = new Date();
	$scope.refundAmount = function(checkinDate, theCost){
		var nowDate = moment();
		var checkinDateMoment = moment(checkinDate);
		var delta = Math.round(moment.duration(checkinDateMoment - nowDate).asDays())
		var refund = 0;
		if(delta <= 1){
			refund = 0;
		}
		else if(delta<4){
			refund =theCost*0.8
		}
		else{
			refund = theCost;
		}
		return refund;
	}

	//"My reservations" links to the update and cancel views with ?id= so the reservation opens without typing its ID
	var linkedId = $location.search().id;
	if(linkedId && !$("#startDatePicker").length){
		$scope.resID = linkedId;
		$scope.findReservation();
	}

})

.controller('myReservationsController', function($rootScope, $scope, reservationFactory){
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.reservations = null; //null until the server answers, so "no reservations" does not flash
	$scope.statusFilter = 'all';
	var PAGE_SIZE = 10; //customers with a long history would get a huge page otherwise
	$scope.visibleCount = PAGE_SIZE;
	var today = moment().format('YYYY-MM-DD');

	$scope.setFilter = function(status){
		$scope.statusFilter = status;
		$scope.visibleCount = PAGE_SIZE;
	}

	$scope.showMore = function(){
		$scope.visibleCount += PAGE_SIZE;
	}

	//compared as YYYY-MM-DD strings so no timezone conversion can shift the day
	$scope.status = function(reservation){
		if(reservation.cancelled_or_not == '1'){
			return 'cancelled';
		}
		if(reservation.checkout_date <= today){
			return 'past';
		}
		if(reservation.checkin_date <= today){
			return 'current';
		}
		return 'upcoming';
	}

	var statusLabels = {upcoming: 'Upcoming', current: 'In progress', past: 'Past', cancelled: 'Cancelled'};
	$scope.statusLabel = function(reservation){
		return statusLabels[$scope.status(reservation)];
	}

	$scope.nights = function(reservation){
		return moment(reservation.checkout_date, 'YYYY-MM-DD').diff(moment(reservation.checkin_date, 'YYYY-MM-DD'), 'days');
	}

	$scope.formatDate = function(isoDate){
		return moment(isoDate, 'YYYY-MM-DD').format('ddd, MMM D, YYYY');
	}

	$scope.count = function(status){
		return ($scope.reservations || []).filter(function(reservation){
			return status == 'all' || $scope.status(reservation) == status;
		}).length;
	}

	$scope.matchesFilter = function(reservation){
		return $scope.statusFilter == 'all' || $scope.status(reservation) == $scope.statusFilter;
	}

	if($rootScope.userType == 'customer'){
		reservationFactory.GetMyReservations().$promise.then(function(data){
			$scope.reservations = data;
		}, function(errorData){
			$scope.reservations = [];
			window.alert(errorMessage(errorData, "Your reservations could not be loaded. Please try again."));
		});
	}
})


.controller('reportController', function($rootScope, $scope, reportFactory){
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.creditCards;
	$scope.resReport;
	$scope.popCatReport = {};
	$scope.revenueReport = {};
	$scope.emptyTable = "";

	$scope.getMonth = function(month){
		if(month==="8"){
			return "August";
		}
		else if(month==="9"){
			return "September";
		}
		else{
			return "";
		}
	}

	//reservation and revenue reports use "YYYY-MM" keys; getMonth stays for the popular room report
	$scope.formatMonth = function(key){
		return moment(key, 'YYYY-MM').format('MMMM YYYY');
	}

	//$resource adds $promise and $resolved to the object, so only the other keys are data
	$scope.hasData = function(report){
		return Object.keys(report || {}).some(function(key){ return key.charAt(0) != '$'; });
	}

	//default range: from the first day of the month 11 months ago up to today
	var today = new Date();
	$scope.range = {
		from: new Date(today.getFullYear(), today.getMonth() - 11, 1),
		to: new Date(today.getFullYear(), today.getMonth(), today.getDate())
	};

	$scope.loadReports = function(){
		if(!$scope.range.from || !$scope.range.to){
			window.alert("Please choose both dates");
			return;
		}
		var params = {from: moment($scope.range.from).format('YYYY-MM-DD'), to: moment($scope.range.to).format('YYYY-MM-DD')};
		var showError = function(response){
			if(response.status == 400){
				window.alert(response.data.message);
			}
		};
		reportFactory.ResReport(params).$promise.then(function(data){
			$scope.resReport=data;
		}, showError);
		reportFactory.RevenueReport(params).$promise.then(function(data){
			$scope.revenueReport=data;
		}, showError);
	}
	$scope.loadReports();

	popCatReportResponse = reportFactory.PopularRoomCatReport();
	popCatReportResponse.$promise.then(function(data){
		$scope.popCatReport=data;
	});



})

.controller('forecastController', function($rootScope, $scope, reportFactory){
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.location = 'Atlanta';
	$scope.forecast = null;
	var chart = null;

	$scope.formatWeek = function(isoDate){
		return moment(isoDate, 'YYYY-MM-DD').format('MMM D, YYYY');
	}

	$scope.priceLabel = function(pct){
		if(pct > 0){
			return '+' + pct + ' %';
		}
		if(pct < 0){
			return pct + ' %';
		}
		return 'No change';
	}

	$scope.loadForecast = function(){
		reportFactory.Forecast({location: $scope.location}).$promise.then(function(data){
			$scope.forecast = data;
			drawChart(data);
		}, function(response){
			if(response.status == 400){
				window.alert(response.data.message);
			}
		});
	}

	function drawChart(data){
		var history = data.history;
		var forecast = data.forecast;
		var toPct = function(week){ return Math.round(week.occupancy * 1000) / 10; };
		var empty = function(){ return null; };

		//the current week is in progress: it sits between both series with no value
		var currentWeek = moment(forecast[0].week_start, 'YYYY-MM-DD').subtract(7, 'days').format('YYYY-MM-DD');
		var weeks = history.map(function(w){ return w.week_start; }).concat([currentWeek], forecast.map(function(w){ return w.week_start; }));
		var historySeries = history.map(toPct).concat([null], forecast.map(empty));
		var forecastSeries = history.map(empty).concat([null], forecast.map(toPct));
		var joinIndex = history.length - 1;
		forecastSeries[joinIndex] = historySeries[joinIndex]; //the dashed line starts at the last real week so both lines join

		if(chart){
			chart.destroy();
		}
		chart = new Chart(document.getElementById('forecastChart'), {
			type: 'line',
			data: {
				labels: weeks.map(function(w){ return moment(w, 'YYYY-MM-DD').format('MMM D'); }),
				datasets: [{
					label: 'History',
					data: historySeries,
					borderColor: '#2a78d6',
					backgroundColor: '#2a78d6',
					borderWidth: 2,
					pointRadius: 4,
					pointHoverRadius: 6
				}, {
					label: 'Forecast',
					data: forecastSeries,
					borderColor: '#eb6834',
					backgroundColor: '#eb6834',
					borderWidth: 2,
					borderDash: [6, 4],
					spanGaps: true,
					pointRadius: function(context){ return context.dataIndex == joinIndex ? 0 : 4; },
					pointHoverRadius: 6
				}]
			},
			options: {
				maintainAspectRatio: false,
				interaction: {mode: 'index', intersect: false},
				scales: {
					y: {
						min: 0,
						max: 100,
						title: {display: true, text: 'Occupancy', color: '#52514e'},
						ticks: {color: '#52514e', callback: function(value){ return value + ' %'; }},
						grid: {color: '#e8e8e5'}
					},
					x: {
						title: {display: true, text: 'Week starting (Monday)', color: '#52514e'},
						ticks: {color: '#52514e'},
						grid: {display: false}
					}
				},
				plugins: {
					legend: {position: 'top', labels: {color: '#0b0b0b'}},
					tooltip: {
						//the join point and the current week have no forecast/history of their own
						filter: function(item){ return item.raw !== null && !(item.datasetIndex == 1 && item.dataIndex == joinIndex); },
						callbacks: {
							title: function(items){ return 'Week of ' + moment(weeks[items[0].dataIndex], 'YYYY-MM-DD').format('MMM D, YYYY'); },
							label: function(item){ return item.dataset.label + ': ' + item.formattedValue + ' %'; }
						}
					}
				}
			}
		});
	}

	$scope.$on('$destroy', function(){
		if(chart){
			chart.destroy();
		}
	});

	if($rootScope.userType == 'manager'){
		$scope.loadForecast();
	}
})


.controller('paymentController', function($rootScope, $scope, paymentFactory){

	$("#expirationDatePicker").datetimepicker(
	{
		format: 'YYYY-MM-DD',
		minDate: new Date()
	});
	
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.creditCards = null; //saved cards: {token, last4, name, expiration_date, is_default}
	$scope.creditCardNumber; //the number for ADDING a card; it is only sent once, never shown again
	$scope.makeDefault = false;

	function loadCards(){
		getCardsResponse = paymentFactory.GetCreditCards({
			"username": $rootScope.currentUser
		});
		getCardsResponse.$promise.then(function(data){
			$scope.creditCards = data; //data is an array
		});
	}
	loadCards();

	$scope.addCard = function(){
		$scope.expirationDate = $("#expirationDatePicker").data("date");
		addCreditCardResponse = paymentFactory.AddCreditCard({
			"username":$rootScope.currentUser,
			"card_number": $scope.creditCardNumber,
			"cvv": $scope.cvv,
			"expiration_date": $scope.expirationDate,
			"name": $scope.cardName, //name of the owner of the card, not necesarilly the username
			"make_default": $scope.makeDefault
		});
		addCreditCardResponse.$promise.then(function(data){
			//the full number and cvv are not kept in the page
			$scope.creditCardNumber = '';
			$scope.cvv = '';
			loadCards();
			window.alert("Card successfully added.");
		},
		function(errorData){
			window.alert(errorMessage(errorData, "The card could not be added. Please check the data and try again."));
		});
	}

	$scope.setDefaultCard = function(card){
		paymentFactory.SetDefaultCreditCard({"token": card.token}).$promise.then(function(data){
			loadCards();
		},
		function(errorData){
			window.alert(errorMessage(errorData, "The default card could not be changed."));
		});
	}

	$scope.deleteCard = function(card){
		if(!window.confirm("Delete the card ending in " + card.last4 + "?")){
			return;
		}
		deleteCreditCardResponse = paymentFactory.DeleteCreditCard({
			"username": $rootScope.currentUser,
			"token": card.token
		}, function(successData)
		{
			loadCards();
			window.alert("Card successfully deleted.");
		},
		function(errorData)
		{
			window.alert(errorMessage(errorData, "The card could not be deleted."));
		});
	}


})

.controller('reviewController', function($rootScope, $scope, reviewFactory){
	$scope.loggedInBool = $rootScope.alreadyLoggedIn();
	$scope.comment = ''; //just in case the user doesn't give one, so in our'd DB, we won't have null, instead we'll have ''
	$scope.viewPart2= false;
	$scope.reviews;
	$scope.emptyTable = '';
	$scope.location="Atlanta";
	$scope.reviews = [];
	$scope.rating = "Neutral";
	$scope.hide = false;

	$scope.addReview = function(){
		addReviewResponse = reviewFactory.AddReview({
			"location": $scope.location, 
			"comment": $scope.comment,
			"rating": $scope.rating, 
			"username": $rootScope.currentUser
		});
	//handle promise
		addReviewResponse.$promise.then(function(data){
			window.alert("Review added!");
		});
	}

	$scope.getReviews = function(){
		getReviewsResponse = reviewFactory.GetReviews({
			"location": $scope.location
		});
		getReviewsResponse.$promise.then(function(data){
			$scope.viewPart2 = true;
			$scope.reviews = data; //this is an array
			if($scope.reviews.length==0 ){
				$scope.emptyTable="Sorry, there are no reviews for this location!";
				$scope.hide = true;
			}
			else{
				$scope.hide = false;
			}
		});
	}

})


.config(function($routeProvider) { //routing needs to be on a server in order to run
	$routeProvider
	.when('/',{
		templateUrl: 'static/views/welcome.html',
	})
	.when('/login', {
		templateUrl: 'static/views/login.html',
		controller: 'loginController'
	})
	.when('/register', {
		templateUrl: 'static/views/registerUser.html',
		controller: 'registerController'
	})
	.when('/portal', { //the page that the user can pick their task on
		templateUrl: 'static/views/selectionPage.html',
		controller: 'portalController'
	})
	.when('/searchroom', {
		templateUrl: 'static/views/searchRoom.html',
		controller: 'reservationController'
	})
	.when('/reserve', {
		templateUrl: 'static/views/searchRoom.html',
		controller: 'reservationController'
	})
	.when('/myReservations', {
		templateUrl: 'static/views/myReservations.html',
		controller: 'myReservationsController'
	})
	.when('/update', {
		templateUrl: 'static/views/updateReservation.html',
		controller: 'reservationController'
	})
	.when('/cancel', {
		templateUrl: 'static/views/cancelReservation.html',
		controller: 'reservationController'
	})
	.when('/payment', {
		templateUrl: 'static/views/payment.html',
		controller: 'paymentController'
	})
	.when('/resReport', {
		templateUrl: 'static/views/reservationReport.html',
		controller: 'reportController'
	})
	.when('/popCatReport', {
		templateUrl: 'static/views/popularRoomCatReport.html',
		controller: 'reportController'
	})
	.when('/revenueReport', {
		templateUrl: 'static/views/revenueReport.html',
		controller: 'reportController'
	})
	.when('/forecastReport', {
		templateUrl: 'static/views/forecastReport.html',
		controller: 'forecastController'
	})
	.when('/provideFeedback', {
		templateUrl: 'static/views/writeReview.html',
		controller: 'reviewController'
	})
	.when('/viewFeedback', {
		templateUrl: 'static/views/viewFeedback.html',
		controller: 'reviewController'
	});
})


