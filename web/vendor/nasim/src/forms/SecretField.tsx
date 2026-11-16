'use client';

import {
  Description,
  FieldError,
  InputGroup,
  Label,
  TextField as HeroTextField,
} from '@heroui/react';
import { type ReactNode, useId, useState } from 'react';
import { tv } from 'tailwind-variants';
import { StatusChip } from '../composites/StatusChip';
import { EyeIcon, EyeOffIcon } from '../icons';
import { Button } from '../primitives';
import { t } from '../strings';
import {
  type Binding,
  type FieldProps,
  type FieldState,
  WithBinding,
  describes,
} from './binding';

const secretField = tv({
  slots: {
    root: 'flex flex-col gap-1.5',
    label: 'text-sm font-medium text-foreground',
    // The stored state is a row, not an input: it is at least as tall as one.
    stored:
      'flex min-h-11 flex-wrap items-center gap-x-3 gap-y-2 rounded-field border border-field-border bg-field-background px-3 py-1.5',
    hint: 'font-mono text-sm text-muted',
    actions: 'ms-auto flex items-center gap-1',
    help: 'text-xs text-muted',
    error: 'text-xs text-danger',
  },
});

// The secret's value is what the form sends: undefined leaves it as it is, '' clears it, text replaces it.
type SecretValue = string | undefined;

type SecretFieldProps = FieldProps &
  Binding<SecretValue> & {
    /** The server holds a value: the field shows it as stored instead of as an input. */
    isSet: boolean;
    /** What the server shows of a stored value (`••••1234`); never the value itself. */
    maskedHint?: string;
  };

// The replace state belongs to the person's press, but a new stored value (after a save) ends it.
function useReplacing(resetKey: string) {
  const [replacing, setReplacing] = useState(false);
  const [seen, setSeen] = useState(resetKey);
  if (seen !== resetKey) {
    setSeen(resetKey);
    setReplacing(false);
  }
  return [replacing, setReplacing] as const;
}

type BodyProps = Omit<SecretFieldProps, keyof Binding<SecretValue>> & {
  field: FieldState<SecretValue>;
};

function SecretBody({
  field,
  label,
  description,
  isRequired,
  isDisabled,
  className,
  'data-testid': testId,
  isSet,
  maskedHint,
}: BodyProps) {
  const slots = secretField();
  const text = field.value;
  const [replacing, setReplacing] = useReplacing(
    `${isSet}|${maskedHint ?? ''}`,
  );
  const [shown, setShown] = useState(false);
  const labelId = useId();
  const helpId = useId();
  const replaceId = useId();
  const clearId = useId();
  const undoId = useId();
  const typing = text !== undefined && text !== '';
  const cleared = isSet && text === '';

  if (isSet && !replacing && !typing) {
    return (
      <div
        role="group"
        aria-labelledby={labelId}
        aria-describedby={description ? helpId : undefined}
        className={slots.root({ className })}
        data-testid={testId}
        data-state={cleared ? 'cleared' : 'set'}
      >
        <span id={labelId} className={slots.label()}>
          {label}
        </span>
        <div className={slots.stored()}>
          {cleared ? (
            <StatusChip tone="warning" size="sm" label={t.secret.willClear} />
          ) : (
            <>
              <StatusChip tone="success" size="sm" label={t.secret.stored} />
              {maskedHint ? (
                <span dir="ltr" className={slots.hint()}>
                  {maskedHint}
                </span>
              ) : null}
            </>
          )}
          <span className={slots.actions()}>
            {cleared ? (
              <Button
                key="undo"
                size="sm"
                variant="secondary"
                isDisabled={isDisabled}
                id={undoId}
                aria-labelledby={`${undoId} ${labelId}`}
                onPress={() => field.onChange(undefined)}
              >
                {t.secret.undoClear}
              </Button>
            ) : (
              <Button
                key="clear"
                size="sm"
                variant="danger-soft"
                isDisabled={isDisabled}
                id={clearId}
                aria-labelledby={`${clearId} ${labelId}`}
                onPress={() => field.onChange('')}
              >
                {t.secret.clear}
              </Button>
            )}
            <Button
              size="sm"
              variant="secondary"
              isDisabled={isDisabled}
              id={replaceId}
              aria-labelledby={`${replaceId} ${labelId}`}
              onPress={() => {
                // a cleared field being replaced is no longer a clear
                if (cleared) field.onChange(undefined);
                setShown(false);
                setReplacing(true);
              }}
            >
              {t.secret.replace}
            </Button>
          </span>
        </div>
        {description ? (
          <p id={helpId} className={slots.help()}>
            {description}
          </p>
        ) : null}
        {field.errorMessage ? (
          <p role="alert" className={slots.error()}>
            {field.errorMessage}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <HeroTextField
      fullWidth
      {...describes(description)}
      name={field.name}
      value={text ?? ''}
      // An empty box sends nothing, as an untouched one does.
      onChange={(next) => field.onChange(next === '' ? undefined : next)}
      onBlur={field.onBlur}
      isInvalid={field.isInvalid}
      isRequired={isRequired && !isSet}
      isDisabled={isDisabled}
      validationBehavior="aria"
      className={className}
      data-testid={testId}
      data-state={isSet ? 'replacing' : 'empty'}
    >
      <div className="flex items-center justify-between gap-2">
        <Label>{label}</Label>
        {isSet ? (
          <Button
            size="sm"
            variant="tertiary"
            onPress={() => {
              field.onChange(undefined);
              setShown(false);
              setReplacing(false);
            }}
          >
            {t.common.cancel}
          </Button>
        ) : null}
      </div>
      <InputGroup fullWidth>
        <InputGroup.Input
          ref={field.inputRef}
          type={shown ? 'text' : 'password'}
          dir="ltr"
          // new-password keeps the browser from filling in a password it saved for the site
          autoComplete="new-password"
          spellCheck={false}
          autoFocus={isSet && replacing}
          className="text-end font-mono"
        />
        <InputGroup.Suffix className="pe-0">
          <Button
            isIconOnly
            size="sm"
            variant="ghost"
            isDisabled={isDisabled}
            aria-label={shown ? t.secret.hide : t.secret.show}
            onPress={() => setShown((current) => !current)}
          >
            {shown ? <EyeOffIcon /> : <EyeIcon />}
          </Button>
        </InputGroup.Suffix>
      </InputGroup>
      {description ? <Description>{description}</Description> : null}
      <FieldError>{field.errorMessage}</FieldError>
    </HeroTextField>
  );
}

// A key, a token or a password the server keeps and never shows again. The field never receives the
// stored value, only whether there is one and a masked hint, and it sends one of three things: nothing
// (undefined, unchanged), the new text, or '' (an explicit clear). In a form by `name`, or controlled.
export function SecretField({
  isSet,
  maskedHint,
  label,
  description,
  isRequired,
  isDisabled,
  className,
  'data-testid': testId,
  ...binding
}: SecretFieldProps): ReactNode {
  return (
    <WithBinding<SecretValue> binding={binding as Binding<SecretValue>}>
      {(field) => (
        <SecretBody
          field={field}
          isSet={isSet}
          maskedHint={maskedHint}
          label={label}
          description={description}
          isRequired={isRequired}
          isDisabled={isDisabled}
          className={className}
          data-testid={testId}
        />
      )}
    </WithBinding>
  );
}
