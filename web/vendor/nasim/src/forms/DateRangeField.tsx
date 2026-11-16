'use client';

import {
  DateField,
  DateRangePicker,
  Description,
  FieldError,
  I18nProvider,
  Label,
  RangeCalendar,
  ToggleButton,
  ToggleButtonGroup,
} from '@heroui/react';
import { BackIcon, ForwardIcon } from '../icons';
import { Button } from '../primitives';
import { t } from '../strings';
import {
  type Binding,
  type FieldProps,
  WithBinding,
  describes,
} from './binding';
import { fromJalaliDate, toJalaliDate } from './jalali';

/** A range of days as the field keeps it: Gregorian `YYYY-MM-DD` for both ends, `''` for no range. */
export type DateRangeValue = { start: string; end: string };

/** A quick choice the app offers beside the calendar: «امروز», «۷ روز گذشته», «این ماه». */
export type DateRangePreset = DateRangeValue & {
  id: string;
  /** The button's words. */
  label: string;
};

const EMPTY: DateRangeValue = { start: '', end: '' };

type DateRangeFieldProps = FieldProps &
  Binding<DateRangeValue> & {
    /** Names the calendar popover. */
    calendarLabel: string;
    /** The text of the button that empties the field. */
    clearLabel: string;
    /** Quick choices under the field, as a segmented group; the app works out their days. */
    presets?: readonly DateRangePreset[];
    /** Names the group of presets; needed with `presets`. */
    presetsLabel?: string;
  };

// A range of days in the Persian calendar with Persian digits. The value stays Gregorian `YYYY-MM-DD`
// for both ends, as a form validates and converts it; the presets are the app's, its own words and days.
export function DateRangeField({
  label,
  description,
  isRequired,
  isDisabled,
  className,
  'data-testid': testId,
  calendarLabel,
  clearLabel,
  presets,
  presetsLabel,
  ...binding
}: DateRangeFieldProps) {
  return (
    <WithBinding<DateRangeValue> binding={binding as Binding<DateRangeValue>}>
      {(field) => {
        const value = field.value ?? EMPTY;
        const start = toJalaliDate(value.start);
        const end = toJalaliDate(value.end);
        const range = start && end ? { start, end } : null;
        return (
          <I18nProvider locale="fa-IR-u-ca-persian">
            <div
              className={['flex w-full flex-col gap-2', className]
                .filter(Boolean)
                .join(' ')}
              data-testid={testId}
            >
              <DateRangePicker
                {...describes(description)}
                value={range}
                onChange={(next) =>
                  field.onChange(
                    next
                      ? {
                          start: fromJalaliDate(next.start),
                          end: fromJalaliDate(next.end),
                        }
                      : EMPTY,
                  )
                }
                onBlur={field.onBlur}
                isInvalid={field.isInvalid}
                isRequired={isRequired}
                isDisabled={isDisabled}
                validationBehavior="aria"
                className="flex w-full flex-col gap-1"
              >
                <Label>{label}</Label>
                {description ? <Description>{description}</Description> : null}
                <DateField.Group fullWidth>
                  <DateField.Input slot="start">
                    {(segment) => <DateField.Segment segment={segment} />}
                  </DateField.Input>
                  <DateRangePicker.RangeSeparator />
                  <DateField.Input slot="end">
                    {(segment) => <DateField.Segment segment={segment} />}
                  </DateField.Input>
                  <DateField.Suffix>
                    {range ? (
                      // slot={null}: not the calendar trigger the picker offers its first button
                      <Button
                        slot={null}
                        variant="tertiary"
                        size="sm"
                        onPress={() => field.onChange(EMPTY)}
                      >
                        {clearLabel}
                      </Button>
                    ) : null}
                    <DateRangePicker.Trigger>
                      <DateRangePicker.TriggerIndicator />
                    </DateRangePicker.Trigger>
                  </DateField.Suffix>
                </DateField.Group>
                <FieldError>{field.errorMessage}</FieldError>
                <DateRangePicker.Popover className="flex min-w-72 flex-col gap-3">
                  <RangeCalendar aria-label={calendarLabel}>
                    <RangeCalendar.Header>
                      {/* HeroUI names this button in English; with no aria-label its name is its text. */}
                      <RangeCalendar.YearPickerTrigger aria-label={undefined}>
                        <RangeCalendar.YearPickerTriggerHeading />
                        <span className="sr-only">
                          ، {t.calendar.selectYear}
                        </span>
                        <RangeCalendar.YearPickerTriggerIndicator />
                      </RangeCalendar.YearPickerTrigger>
                      {/* HeroUI un-turns its chevrons inside a picker: these turn themselves. */}
                      <RangeCalendar.NavButton slot="previous">
                        <BackIcon className="size-4 rtl:rotate-180" />
                      </RangeCalendar.NavButton>
                      <RangeCalendar.NavButton slot="next">
                        <ForwardIcon className="size-4 rtl:rotate-180" />
                      </RangeCalendar.NavButton>
                    </RangeCalendar.Header>
                    {/* Narrow weekday names (ش ی د س چ پ ج): full Persian names do not fit seven columns. */}
                    <RangeCalendar.Grid weekdayStyle="narrow">
                      <RangeCalendar.GridHeader>
                        {(day) => (
                          <RangeCalendar.HeaderCell>
                            {day}
                          </RangeCalendar.HeaderCell>
                        )}
                      </RangeCalendar.GridHeader>
                      <RangeCalendar.GridBody>
                        {(date) => <RangeCalendar.Cell date={date} />}
                      </RangeCalendar.GridBody>
                    </RangeCalendar.Grid>
                    <RangeCalendar.YearPickerGrid>
                      <RangeCalendar.YearPickerGridBody>
                        {({ year }) => (
                          <RangeCalendar.YearPickerCell year={year} />
                        )}
                      </RangeCalendar.YearPickerGridBody>
                    </RangeCalendar.YearPickerGrid>
                  </RangeCalendar>
                </DateRangePicker.Popover>
              </DateRangePicker>
              {presets?.length ? (
                <Presets
                  presets={presets}
                  label={presetsLabel}
                  value={value}
                  isDisabled={isDisabled}
                  onChange={field.onChange}
                />
              ) : null}
            </div>
          </I18nProvider>
        );
      }}
    </WithBinding>
  );
}

// A segmented group of the app's quick choices: the one whose days are the field's value is chosen.
function Presets({
  presets,
  label,
  value,
  isDisabled,
  onChange,
}: {
  presets: readonly DateRangePreset[];
  label?: string;
  value: DateRangeValue;
  isDisabled?: boolean;
  onChange: (value: DateRangeValue) => void;
}) {
  const chosen = presets.find(
    (preset) => preset.start === value.start && preset.end === value.end,
  );
  return (
    <div className="-m-1 max-w-full overflow-x-auto p-1">
      <ToggleButtonGroup
        aria-label={label}
        size="sm"
        selectionMode="single"
        disallowEmptySelection
        isDisabled={isDisabled}
        selectedKeys={chosen ? [chosen.id] : []}
        onSelectionChange={(keys) => {
          const preset = presets.find((one) => keys.has(one.id));
          if (preset) onChange({ start: preset.start, end: preset.end });
        }}
      >
        {presets.map((preset, index) => (
          <ToggleButton
            key={preset.id}
            id={preset.id}
            className="pointer-coarse:min-h-11"
          >
            {index > 0 ? <ToggleButtonGroup.Separator /> : null}
            {preset.label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </div>
  );
}
