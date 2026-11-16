'use client';

import {
  Description,
  FieldError,
  Label,
  NumberField as HeroNumberField,
} from '@heroui/react';
import type { ComponentProps } from 'react';
import { t } from '../strings';
import {
  type Binding,
  type FieldProps,
  WithBinding,
  describes,
} from './binding';

type NumberFieldProps = FieldProps &
  Binding<number | undefined> &
  Pick<
    ComponentProps<typeof HeroNumberField>,
    'minValue' | 'maxValue' | 'step' | 'formatOptions'
  > & {
    /** No − and + buttons: for a number that is an identifier (a Telegram id), not a quantity. */
    hideSteppers?: boolean;
    /**
     * Report the value on every keystroke, not only when the box is left or Enter is pressed (React
     * Aria's way): for a price or a filter that follows what is typed. A half-typed number (a lone
     * minus) is not reported until it is one.
     */
    reportWhileTyping?: boolean;
  };

// React Aria words these from its string dictionary, which a server render cannot reach (it would
// say "Increase" in the page's HTML), so they are named here from the same Persian strings.
const words = t.reactAria['@react-aria/numberfield'];

const DIGITS = '۰۱۲۳۴۵۶۷۸۹';
const ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩';

// The number in what is typed, Persian or Arabic digits and separators included; undefined while the box
// is empty, NaN while the text is not yet a number.
function typedNumber(text: string): number | undefined {
  const latin = text
    .replace(/[۰-۹]/g, (digit) => String(DIGITS.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(ARABIC_DIGITS.indexOf(digit)))
    .replace(/[٬,\s]/g, '')
    .replace('٫', '.');
  return latin === '' ? undefined : Number(latin);
}

// The value is a number, or undefined while the box is empty (React Aria reports NaN).
export function NumberField({
  label,
  description,
  isRequired,
  isDisabled,
  className,
  'data-testid': testId,
  hideSteppers,
  reportWhileTyping,
  minValue,
  maxValue,
  step,
  formatOptions,
  ...binding
}: NumberFieldProps) {
  const fieldLabel = typeof label === 'string' ? label : '';
  return (
    <WithBinding<number | undefined>
      binding={binding as Binding<number | undefined>}
    >
      {(field) => (
        <HeroNumberField
          {...describes(description)}
          fullWidth
          name={field.name}
          value={field.value ?? Number.NaN}
          onChange={(value) =>
            field.onChange(Number.isNaN(value) ? undefined : value)
          }
          onBlur={field.onBlur}
          isInvalid={field.isInvalid}
          isRequired={isRequired}
          isDisabled={isDisabled}
          validationBehavior="aria"
          className={className}
          data-testid={testId}
          minValue={minValue}
          maxValue={maxValue}
          step={step}
          formatOptions={formatOptions}
        >
          <Label>{label}</Label>
          <HeroNumberField.Group>
            {hideSteppers ? null : (
              <HeroNumberField.DecrementButton
                aria-label={words.decrease({ fieldLabel })}
              />
            )}
            <HeroNumberField.Input
              ref={field.inputRef}
              aria-roledescription={words.numberField}
              onChange={
                reportWhileTyping
                  ? (event) => {
                      const typed = typedNumber(event.currentTarget.value);
                      if (typed === undefined || !Number.isNaN(typed))
                        field.onChange(typed);
                    }
                  : undefined
              }
            />
            {hideSteppers ? null : (
              <HeroNumberField.IncrementButton
                aria-label={words.increase({ fieldLabel })}
              />
            )}
          </HeroNumberField.Group>
          {description ? <Description>{description}</Description> : null}
          <FieldError>{field.errorMessage}</FieldError>
        </HeroNumberField>
      )}
    </WithBinding>
  );
}
