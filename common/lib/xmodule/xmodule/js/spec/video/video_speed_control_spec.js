(function (undefined) {
    describe('VideoSpeedControl', function () {
        var state, oldOTBD;

        beforeEach(function () {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine.createSpy('onTouchBasedDevice')
                .andReturn(null);
        });

        afterEach(function () {
            $('source').remove();
            window.onTouchBasedDevice = oldOTBD;
        });

        describe('constructor', function () {
            describe('always', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();
                });

                it('add the video speed control to player', function () {
                    var li, secondaryControls;

                    secondaryControls = $('.secondary-controls');
                    li = secondaryControls.find('.video_speeds li');

                    expect(secondaryControls).toContain('.speeds');
                    expect(secondaryControls).toContain('.video_speeds');
                    expect(secondaryControls.find('p.active').text())
                        .toBe('1.50x');
                    expect(li.filter('.active')).toHaveData(
                        'speed', state.videoSpeedControl.currentSpeed
                    );
                    expect(li.length).toBe(state.videoSpeedControl.speeds.length);

                    $.each(li.toArray().reverse(), function (index, link) {
                        expect($(link)).toHaveData(
                            'speed', state.videoSpeedControl.speeds[index]
                        );
                        expect($(link).find('a').text()).toBe(
                            state.videoSpeedControl.speeds[index] + 'x'
                        );
                    });
                });

                it('add ARIA attributes to speed control', function () {
                    var speedControl = $('div.speeds>a');

                    expect(speedControl).toHaveAttrs({
                        'role': 'button',
                        'title': 'Speeds',
                        'aria-disabled': 'false'
                    });
                });

                it('bind to change video speed link', function () {
                    expect($('.video_speeds a')).toHandleWith(
                        'click', state.videoSpeedControl.changeVideoSpeed
                    );
                });
            });

            describe('when running on touch based device', function () {
                $.each(['iPad', 'Android'], function (index, device) {
                    it('is not rendered on' + device, function () {
                        window.onTouchBasedDevice.andReturn([device]);
                        state = jasmine.initializePlayer();

                        expect(state.el.find('div.speeds')).not.toExist();
                    });
                });
            });

            describe('when running on non-touch based device', function () {
                var speedControl, speedEntries,
                    KEY = $.ui.keyCode;

                keyPressEvent = function(key) {
                    return $.Event('keydown', {keyCode: key});
                };

                // Get previous element in array or cyles back to the last if it
                // is the first.
                previousSpeed = function(index) {
                    return index === 0 ?
                                     speedEntries.eq(speedEntries.length - 1) :
                                     speedEntries.eq(index - 1);
                }

                // Get next element in array or cyles back to the first if it is
                // the last.
                nextSpeed = function(index) {
                    return index === speedEntries.length - 1 ?
                                     speedEntries.eq(0) :
                                     speedEntries.eq(index + 1);
                }

                beforeEach(function () {
                    state = jasmine.initializePlayer();
                    speedControl = $('div.speeds');
                    speedEntries = $('div.speeds>a');
                    spyOn($.fn, 'focus');
                });

                it('open the speed toggle on hover', function () {
                    speedControl.mouseenter();
                    expect(speedControl).toHaveClass('open');
                    speedControl.mouseleave();
                    expect(speedControl).not.toHaveClass('open');
                });

                it('close the speed toggle on mouse out', function () {
                    speedControl.mouseenter().mouseleave();
                    expect(speedControl).not.toHaveClass('open');
                });

                it('close the speed toggle on click', function () {
                    speedControl.mouseenter().click();
                    expect(speedControl).not.toHaveClass('open');
                });

                it('open/close the speed toggle on ENTER keydown', function () {
                    speedControl.trigger(keyPressEvent(KEY.ENTER));
                    expect(speedControl).toHaveClass('open');
                    speedControl.trigger(keyPressEvent(KEY.ENTER));
                    expect(speedControl).not.toHaveClass('open');
                });

                it('open/close the speed toggle on SPACE keydown', function () {
                    speedControl.trigger(keyPressEvent(KEY.SPACE));
                    expect(speedControl).toHaveClass('open');
                    speedControl.trigger(keyPressEvent(KEY.SPACE));
                    expect(speedControl).not.toHaveClass('open');
                });

                it('open the speed toggle on UP keydown', function () {
                    $('div.speeds').trigger(keyPressEvent(KEY.UP));
                    expect($('div.speeds')).toHaveClass('open');
                    expect(speedEntries.last().focus).toHaveBeenCalled();
                });

                it('close the speed toggle on ESC keydown', function () {
                    speedControl.trigger(keyPressEvent($.ui.keyCode.ESC));
                    expect(speedControl).not.toHaveClass('open');
                });

                it('UP and DOWN keydown function as expected', function () {
                    // Iterate through list in both directions and check if
                    // things wrap up correctly.
                    var lastEntry = speedEntries.length-1, i;

                    // First open menu
                    speedControl.trigger(keyPressEvent(KEY.UP));

                    // Iterate with UP key until we have looped.
                    for (i = lastEntry; i >= 0; i--) {
                        speedEntries.eq(i).trigger(keyPressEvent(KEY.UP));
                        expect(previousSpeed(i).focus).toHaveBeenCalled();
                    }

                    // Iterate with DOWN key until we have looped.
                    for (i = 0; i <= lastEntry; i++) {
                        speedEntries.eq(i).trigger(keyPressEvent(KEY.DOWN));
                        expect(nextSpeed(i).focus).toHaveBeenCalled();
                    }
                });
            });
        });

        describe('changeVideoSpeed', function () {
            // This is an unnecessary test. The internal browser API, and
            // YouTube API detect (and do not do anything) if there is a
            // request for a speed that is already set.
            //
            //     describe("when new speed is the same") ...

            describe('when new speed is not the same', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();
                    state.videoSpeedControl.setSpeed(1.0);
                    spyOn(state.videoPlayer, 'onSpeedChange').andCallThrough();

                    $('li[data-speed="0.75"] a').click();
                });

                it('trigger speedChange event', function () {
                    expect(state.videoPlayer.onSpeedChange).toHaveBeenCalled();
                    expect(state.videoSpeedControl.currentSpeed).toEqual(0.75);
                });
            });

            describe(
                'make sure the speed control gets the focus afterwards',
                function ()
            {
                var anchor;

                beforeEach(function () {
                    state = jasmine.initializePlayer();
                    anchor= $('.speeds > a').first();
                    state.videoSpeedControl.setSpeed(1.0);
                    spyOnEvent(anchor, 'focus');
                });

                it('when the speed is the same', function () {
                    $('li[data-speed="1.0"] a').click();
                    expect('focus').toHaveBeenTriggeredOn(anchor);
                });

                it('when the speed is not the same', function () {
                    $('li[data-speed="0.75"] a').click();
                    expect('focus').toHaveBeenTriggeredOn(anchor);
                });
            });
        });

        describe('onSpeedChange', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();
                $('li[data-speed="1.0"] a').addClass('active');
                state.videoSpeedControl.setSpeed(0.75);
            });

            it('set the new speed as active', function () {
                expect($('.video_speeds li[data-speed="1.0"]'))
                    .not.toHaveClass('active');
                expect($('.video_speeds li[data-speed="0.75"]'))
                    .toHaveClass('active');
                expect($('.speeds p.active')).toHaveHtml('0.75x');
            });
        });
    });
}).call(this);
