'use client';

import {
  ComboBox,
  Description,
  FieldError,
  Input,
  Label,
  ListBox,
  Tag,
  TagGroup,
} from '@heroui/react';
import { Button } from '../primitives';
import { t } from '../strings';
import {
  type Binding,
  type FieldProps,
  WithBinding,
  describes,
} from './binding';

type MultiSelectProps = FieldProps &
  Binding<string[]> & {
    options: readonly { value: string; label: string; isDisabled?: boolean }[];
    /** Defaults to «جست‌وجو و انتخاب». */
    placeholder?: string;
  };

// Several of a list's options (a few panels, servers, plans): a combo box that searches and keeps choosing,
// and what is chosen below it as tags, each with its own remove button and one «پاک کردن همه». In a form
// the value is the array of the chosen `value`s, in the order they were chosen; undefined counts as none.
export function MultiSelect({
  label,
  description,
  isRequired,
  isDisabled,
  className,
  'data-testid': testId,
  options,
  placeholder = t.multiSelect.placeholder,
  ...binding
}: MultiSelectProps) {
  return (
    <WithBinding<string[]> binding={binding as Binding<string[]>}>
      {(field) => {
        const chosen = field.value ?? [];
        return (
          <div
            className={['flex w-full flex-col gap-2', className]
              .filter(Boolean)
              .join(' ')}
            data-testid={testId}
          >
            <ComboBox
              fullWidth
              {...describes(description)}
              selectionMode="multiple"
              allowsEmptyCollection
              value={chosen}
              onChange={(keys) => field.onChange(keys.map(String))}
              onBlur={field.onBlur}
              isInvalid={field.isInvalid}
              isRequired={isRequired}
              isDisabled={isDisabled}
              disabledKeys={options
                .filter((option) => option.isDisabled)
                .map((option) => option.value)}
              validationBehavior="aria"
            >
              <Label>{label}</Label>
              <ComboBox.InputGroup>
                <Input ref={field.inputRef} placeholder={placeholder} />
                <ComboBox.Trigger />
              </ComboBox.InputGroup>
              {description ? <Description>{description}</Description> : null}
              <FieldError>{field.errorMessage}</FieldError>
              <ComboBox.Popover>
                <ListBox
                  selectionMode="multiple"
                  renderEmptyState={() => (
                    <p className="p-3 text-sm text-muted">
                      {t.multiSelect.noResults}
                    </p>
                  )}
                >
                  {options.map((option) => (
                    <ListBox.Item
                      key={option.value}
                      id={option.value}
                      textValue={option.label}
                    >
                      {option.label}
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  ))}
                </ListBox>
              </ComboBox.Popover>
            </ComboBox>
            {chosen.length ? (
              <div className="flex items-start justify-between gap-2">
                <TagGroup
                  aria-label={t.multiSelect.selected}
                  disabledKeys={isDisabled ? chosen : undefined}
                  onRemove={(keys) =>
                    field.onChange(chosen.filter((value) => !keys.has(value)))
                  }
                >
                  <TagGroup.List
                    className="pointer-coarse:gap-3"
                    items={chosen.map((value) => ({
                      id: value,
                      label:
                        options.find((option) => option.value === value)
                          ?.label ?? value,
                    }))}
                  >
                    {(tag) => (
                      <Tag id={tag.id} textValue={tag.label}>
                        {({ allowsRemoving }) => (
                          <>
                            {tag.label}
                            {allowsRemoving ? (
                              <Tag.RemoveButton
                                aria-label={t.multiSelect.remove}
                              />
                            ) : null}
                          </>
                        )}
                      </Tag>
                    )}
                  </TagGroup.List>
                </TagGroup>
                <Button
                  variant="tertiary"
                  size="sm"
                  isDisabled={isDisabled}
                  onPress={() => field.onChange([])}
                >
                  {t.multiSelect.clear}
                </Button>
              </div>
            ) : null}
          </div>
        );
      }}
    </WithBinding>
  );
}
